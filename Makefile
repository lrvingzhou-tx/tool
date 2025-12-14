PYTHON ?= python3
PIP ?= $(PYTHON) -m pip

.PHONY: install run

install:
	$(PIP) install -r requirements.txt

run:
	# 使用 PORT 环境变量覆盖端口，例如: make run PORT=8502
	./scripts/run.sh
