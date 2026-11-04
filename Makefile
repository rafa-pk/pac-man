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
APP = Pacman42
BUILD = build
DIST = dist
OS = $(shell uname -s | tr A-Z a-z)
ARCH = $(shell uname -m)
ZIP = $(APP)-$(OS)-$(ARCH).zip
# app icons must be square: pacman.png is centred on a transparent square
ICON_SIZE = 512

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

package: install
	mkdir -p $(BUILD)
	uv run $(PY) -c "from PIL import Image; \
		img = Image.open('assets/pacman.png').convert('RGBA'); \
		icon = Image.new('RGBA', ($(ICON_SIZE), $(ICON_SIZE))); \
		icon.paste(img, (($(ICON_SIZE) - img.width) // 2, \
		($(ICON_SIZE) - img.height) // 2)); icon.save('$(BUILD)/icon.png')"
	uv run pyinstaller --noconfirm --windowed --name $(APP) \
		--paths $(CURDIR) --icon $(CURDIR)/$(BUILD)/icon.png \
		--add-data "$(CURDIR)/assets:assets" \
		--add-data "$(CURDIR)/$(CONFIG):." \
		--workpath $(BUILD) --specpath $(BUILD) --distpath $(DIST) \
		$(NAME)
	rm -f $(DIST)/$(ZIP)
ifeq ($(OS),darwin)
	cd $(DIST) && zip -qry $(ZIP) $(APP).app
else
	cd $(DIST) && zip -qry $(ZIP) $(APP)
endif
	@echo Package ready: $(DIST)/$(ZIP)

lint:
	uv run flake8 . --exclude=.venv,mazegenerator,$(BUILD),$(DIST)
	uv run mypy . --ignore-missing-imports

lint-strict:
	uv run flake8 . --exclude=.venv,mazegenerator,$(BUILD),$(DIST)
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
	rm -rf $(BUILD)/ $(DIST)/
	@echo Project reset complete