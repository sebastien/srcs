PYTHON=python
PATH_SOURCES_PY=src/py
SOURCES_PY:=$(wildcard $(PATH_SOURCES_PY)/*.py $(PATH_SOURCES_PY)/*/*.py $(PATH_SOURCES_PY)/*/*/*.py $(PATH_SOURCES_PY)/*/*/*/*.py)
MODULES_PY:=$(filter-out %/__main__,$(filter-out %/__init__,$(SOURCES_PY:$(PATH_SOURCES_PY)/%.py=%)))
PYTHON_VERSION?=3.11
PYTHON?=python$(PYTHON_VERSION)
FLAKE8?=flake8
BLACK?=black
MYPYC?=mypyc
BANDIT?=bandit
LPYTHON?=lpython
SHEDSKIN?=shedskin
PYANALYZE?=pyanalyze

PYTHON_MODULE=$(notdir $(firstword $(wildcard $(PATH_SOURCES_PY)/*)))


check: lint audit
	@echo "OK"

audit: require-py-bandit
	@$(BANDIT) -r $(PATH_SOURCES_PY)

# NOTE: The compilation seems to create many small modules instead of a big single one
compile-mypyc: require-py-mypyc
	# NOTE: Output is going to be like '$(PYTHON_MODULE)/__init__.cpython-310-x86_64-linux-gnu.so'
	@$(foreach M,$(MODULES_PY),mkdir -p build/$M;)
	env -C build MYPYPATH=$(realpath .)/src/py $(MYPYC) -p $(PYTHON_MODULE)

compile-shedskin: require-py-shedskin
	@mkdir -p dist
	PYTHONPATH=$(PATH_SOURCES_PY):$(PYTHONPATH) $(SHEDSKIN) build -e $(PYTHON_MODULE)


compile-lpython:
	@mkdir -p dist
	$(LPYTHON) $(SOURCES_PY) -I/usr/lib/python/python3.11/site-packages -I/usrc/lib64/python3.11 -o dist/$(PYTHON_MODULE)

lint: require-py-flake8 require-py-pyanalyze
	@$(FLAKE8) --ignore=E1,E203,E302,E401,E501,E741,F821,W $(SOURCES_PY)
	@$(PYANALYZE) $(SOURCES_PY)



format: require-py-black
	@$(BLACK) $(SOURCES_PY)

require-py-%:
	@if [ -z "$$(which '$*' 2> /dev/null)" ]; then $(PYTHON) -mpip install --user --upgrade '$*'; fi

print-%:
	$(info $*=$($*))

.PHONY: audit check compile lint format
# EOF
