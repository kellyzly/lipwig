 rm -rf explain.dot explain.svg
 python lipwig.py --simple $1 > explain.dot

 dot -Tsvg -o explain.svg explain.dot
