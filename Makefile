SOURCES=$(shell python3 scripts/read-config.py --sources )
FAMILY=$(shell python3 scripts/read-config.py --family )
DRAWBOT_SCRIPTS=$(shell ls documentation/*.py)
DRAWBOT_OUTPUT=$(shell ls documentation/*.py | sed 's/\.py/.png/g')

help:
	@echo "###"
	@echo "# Build targets for $(FAMILY)"
	@echo "###"
	@echo
	@echo "  make build:  Builds the fonts and places them in the fonts/ directory"
	@echo "  make test:   Tests the fonts with fontspector"
	@echo "  make proof:  Creates HTML proof documents in the proof/ directory"
	@echo "  make images: Creates PNG specimen images in the documentation/ directory"
	@echo

build: build.stamp

venv: venv/touchfile

customize: venv
	. venv/bin/activate; python3 scripts/customize.py

build.stamp: venv sources/config.yaml $(SOURCES)
	rm -rf fonts
	(for config in sources/config*.yaml; do . venv/bin/activate; gftools builder $$config; done) && \
	. venv/bin/activate; find fonts -name "*.ttf" | xargs python3 scripts/fix_fonts.py && \
	{ [ -f "fonts/variable/Scoutie-Sans[wght].ttf" ] && mv "fonts/variable/Scoutie-Sans[wght].ttf" "fonts/variable/ScoutieSans[wght].ttf" || true; } && \
	{ [ -f "fonts/variable/Scoutie-Sans-Italic[wght].ttf" ] && mv "fonts/variable/Scoutie-Sans-Italic[wght].ttf" "fonts/variable/ScoutieSans-Italic[wght].ttf" || true; } && \
	{ [ -f "fonts/webfonts/Scoutie-Sans[wght].woff2" ] && mv "fonts/webfonts/Scoutie-Sans[wght].woff2" "fonts/webfonts/ScoutieSans[wght].woff2" || true; } && \
	{ [ -f "fonts/webfonts/Scoutie-Sans-Italic[wght].woff2" ] && mv "fonts/webfonts/Scoutie-Sans-Italic[wght].woff2" "fonts/webfonts/ScoutieSans-Italic[wght].woff2" || true; } && \
	for vf in fonts/variable/*.ttf; do \
		[ -f "$$vf" ] || continue; \
		python3 -c "from fontTools.ttLib import TTFont; import sys; p=sys.argv[1]; f=TTFont(p); f.flavor='woff'; f.save(p[:-4]+'.woff'); f=TTFont(p); f.flavor='woff2'; f.save(p[:-4]+'.woff2')" "$$vf"; \
	done && \
	touch build.stamp

venv/touchfile: requirements.txt
	test -d venv || python3 -m venv venv
	. venv/bin/activate; pip install -Ur requirements.txt
	touch venv/touchfile

test: build.stamp
	which fontspector || (echo "fontspector not found. Please install it with 'cargo install fontspector'." && exit 1)
	TOCHECK=$$(find fonts/variable -type f -name "*.ttf" 2>/dev/null); if [ -z "$$TOCHECK" ]; then TOCHECK=$$(find fonts/ttf -type f -name "*.ttf" 2>/dev/null); fi ; mkdir -p out/ out/fontspector; fontspector --profile googlefonts -l warn --full-lists --succinct --html out/fontspector/fontspector-report.html --ghmarkdown out/fontspector/fontspector-report.md --badges out/badges $$TOCHECK  || echo '::warning file=sources/config.yaml,title=fontspector failures::The fontspector QA check reported errors in your font. Please check the generated report.'

proof: venv build.stamp
	TOCHECK=$$(find fonts/variable -type f -name "*.ttf" 2>/dev/null); if [ -z "$$TOCHECK" ]; then TOCHECK=$$(find fonts/ttf -type f -name "*.ttf" 2>/dev/null); fi ; . venv/bin/activate; mkdir -p out/ out/proof; diffenator2 proof $$TOCHECK -o out/proof

images: venv $(DRAWBOT_OUTPUT)

%.png: %.py build.stamp
	. venv/bin/activate; python3 $< --output $@

clean:
	rm -rf venv
	find . -name "*.pyc" -delete

update-project-template:
	npx update-template https://github.com/googlefonts/googlefonts-project-template/

update: venv
	venv/bin/pip install --upgrade pip-tools
	# See https://pip-tools.readthedocs.io/en/latest/#a-note-on-resolvers for
	# the `--resolver` flag below.
	venv/bin/pip-compile --upgrade --verbose --resolver=backtracking requirements.in
	venv/bin/pip-sync requirements.txt

	git commit -m "Update requirements" requirements.txt
	git push
