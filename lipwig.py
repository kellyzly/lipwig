import sys
import json
import textwrap

from cgi import escape

def ifseteq(h, k, v):
	return h.has_key(k) and h[k] == v
def lwrap(t):
	return "<br/>".join(textwrap.wrap(t, 32))

class TezVertex(object):
	def __init__(self, dag, name, raw):
		self.name = name
		self.raw = raw
		self.vectorized = False
		self.parents = []
		self.prefix = name.replace(" ", "_")
		for k in raw:
			if k == "Execution mode:":
				self.vectorized = raw[k] == "vectorized"
			elif k.find("Operator Tree"):
				self.tree = raw[k]
				# annoying details Map operator uses a list
				# (tez won't do tagged joins)
				if type(self.tree) is list:
					assert len(self.tree) == 1
					self.tree = self.tree.pop()
	def draw(self):
		self.nodes = 0
		print "subgraph cluster_%s {" % self.prefix 
		print 'style=dashed ;' 
		print "compound=true;"
		print "rank=same;"
		print 'label="%s";' % self.name
		self.drawOp(self.tree, None)
		print "}"

	def drawOp(self, ops, parent=None):
		important_keys = set([
#			"outputColumnNames:",
			"expressions:",
			"key expressions:",
			"value expressions:",
			"alias:",
			"aggregations:",
			"keys:",
			"Map-reduce partition columns:"
		])
		for (k,v) in ops.items():
			nodeid = self.nodes
			name = "%s_%d" % (self.prefix, nodeid)
			self.nodes += 1
			if parent:
				print "%s -> %s [weight=1];" % (parent, name) 
			children = False
			text = ["<tr><td colspan=\"2\"><b>%s</b></td></tr>" % k]
			for k1,v1 in v.items():
				if (k1 == "children" and v1): 
					self.drawOp(v1, name)
				elif k1 == "Statistics:":
					rows = v1[v1.find("Num rows:")+len("Num rows:"):v1.find("Data size:")]
					text.insert(1,"<tr><td>Rows:</td><td>%s</td></tr>" % rows)
				else:
					text.append("<tr><td>%s</td><td>%s</td></tr>" % (lwrap(k1), lwrap(escape(json.dumps(v1)))))
			#print '%s [label="%s"];' % (name, k)
			if v.items():
				print '%s [shape=plaintext,label=<%s>];' % (name, "<table>%s</table>" % "\n".join(text)) 
			else:
				print '%s [label=<%s>];' % (name, k) 
				

	def connect(self):
		for (i, t, p) in self.parents:
			pprefix = p.name.replace(" ", "_")
			print '%s_%d -> %s_0 [label="%s", weight=100];' % (pprefix, p.nodes-1, self.prefix, t)


class HiveTezDag(object):
	def __init__(self, q, raw):
		raw = raw["Tez"]
		self.query = q
		self.name = raw["DagName:"]
		self.edges = raw["Edges:"]
		self.vertices = [TezVertex(self, k,v) for (k,v) in raw["Vertices:"].items()]
		vmap = dict([(v.name, v) for v in self.vertices])
		for k,v in self.edges.items():
			child = vmap[k]
			if type(v) is dict: v = [v]
			for (i,p) in enumerate(v):
				child.parents.append((i, p["type"], vmap[p["parent"]]))
	def draw(self):
		[v.draw() for v in self.vertices]
		[v.connect() for v in self.vertices]

class HivePlan(object):
	def __init__(self, q, raw):
		self.raw = raw
		plans = [(k,HiveTezDag(q, v)) for (k,v) in raw["STAGE PLANS"].items() if v.has_key("Tez")]
		assert len(plans) == 1
		self.plan = plans.pop()
	def draw(self):
		print "digraph g {"
		print "node [shape=box];"
		print 'node [id="\N"];'
		print ""
		self.plan[1].draw()
		print "}"

def main(argv):
	p = [HivePlan(f, json.load(open(f))) for f in argv]
	[x.draw() for x in p]

if __name__ == "__main__":
	main(sys.argv[1:])