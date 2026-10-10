# **************************************************************************** #
#                                                                              #
#                                                         :::      ::::::::    #
#    Makefile                                           :+:      :+:    :+:    #
#                                                     +:+ +:+         +:+      #
#    By: rvaz-da- <rvaz-da-@student.s19.be>         +#+  +:+       +#+         #
#                                                 +#+#+#+#+#+   +#+            #
#    Created: 2026/09/30 15:16:20 by rvaz-da-          #+#    #+#              #
#    Updated: 2026/09/30 15:16:21 by rvaz-da-         ###   ########.fr        #
#                                                                              #
# **************************************************************************** #

NAME = pac-man.py
CONFIG = config.json
VENV = .venv
PY = python
WHL = mazegenerator-2.1.0-py3-none-any.whl

install:
	uv python install 3.12
	uv sync
	$(PY) -m zipfile -e $(WHL) .
	rm -rf mazegenerator-2.1.0.dist-info/
	@echo Virtual environment setup complete!

run: install
	uv run $(PY) $(NAME) $(CONFIG)

debug:
	uv run $(PY) -m pdb $(NAME) $(CONFIG)

lint:
	uv run flake8 . --exclude=.venv --exclude=mazegenerator
	uv run mypy . --ignore-missing-imports

lint-strict:
	uv run flake8 . --exclude=.venv --exclude=mazegenerator
	uv run mypy --strict . --ignore-missing-imports

clean:
	rm -rf __pycache__/
	rm -rf .mypy_cache/
	rm -rf .pytest_cache
	find . -type f -name "*.pyc" -delete
	@echo Project cleanup complete!

fclean: clean
	rm -rf .venv/
	rm -rf mazegenerator/
	rm -rf mazegenerator-2.1.0.dist-info/
	@echo Project reset complete