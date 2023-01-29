PY_SRC = $(wildcard */*.py)

all : lint

lint : FORCE
	-MYPYPATH=typeshed mypy $(PY_SRC)
	-TERM=dumb bandit $(PY_SRC)
	-pylint --rcfile=.pylintrc $(PY_SRC)

FORCE :

.PHONY : FORCE all
