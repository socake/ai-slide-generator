# aippt — 常用命令
.PHONY: help install fmt lint typecheck test demo cli verify clean
PYTHON ?= python

help:
	@echo "install    安装依赖到当前虚拟环境"
	@echo "lint       ruff check"
	@echo "typecheck  mypy packages"
	@echo "test       pytest"
	@echo "demo       跑 5 套公开开发集,产出到 demos/(默认 mock 离线零成本)"
	@echo "cli        单条命令: make cli IN=examples/python_intro.json OUT=out.pptx"
	@echo "verify     一键验收: lint+typecheck+test+demo"
	@echo "clean      清理缓存"

install:
	pip install -r requirements.txt

fmt:
	ruff format .

lint:
	ruff check .

typecheck:
	mypy packages

test:
	pytest

# 一键验收:三件套 + 5 套 demo 全绿即可交付
verify: lint typecheck test demo
	@echo "✅ verify 通过 —— lint + typecheck + test + demo 全绿"

# 招聘题验收入口:单条命令吃 JSON 吐 PPTX
cli:
	$(PYTHON) cli.py generate $(IN) $(OUT)

# 跑 5 套公开开发集(默认 mock 离线;真实 LLM 数据见 demos/ 与 DESIGN.md §5)
# 复现真实数据: make demo PROVIDER=deepseek  (需先配 key)
PROVIDER ?= mock
demo:
	@for f in python_intro annual_review coffee_beans rust_order_system kyoto_weekend; do \
		$(PYTHON) cli.py generate examples/$$f.json demos/pptx/$$f.pptx \
			--spec-out demos/specs/$$f.deck.json \
			--benchmark-out demos/benchmark/$$f.benchmark.json \
			--provider $(PROVIDER) ; \
	done

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .mypy_cache .ruff_cache
