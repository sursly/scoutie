SOURCES=$(shell python3 scripts/read-config.py --sources )
FAMILY=$(shell python3 scripts/read-config.py --family )
DRAWBOT_SCRIPTS=$(shell ls documentation/*.py)
DRAWBOT_OUTPUT=$(shell ls documentation/*.py | sed 's/\.py/.png/g')

# Options for ttfautohint on the static TTFs (same flags as the ttfautohint CLI).
#   -x 0  keep x-height at its natural pixel rounding (the default, -x 14, rounds
#         it up at 6-14ppem, stretching text 11-25% taller than designed)
#   -a qss  stem widths: quantized in grayscale, strong (snapped to whole pixels)
#         in GDI and DirectWrite ClearType. DirectWrite (Windows browsers) only
#         uses vertical hints, so this makes crossbars and horizontal strokes
#         land on single pixel rows instead of a dark row plus a faint one.
# Not used: -X 6-60 (no x-height snapping). It brings hinted heights closer to
#   the design (x-height snapping makes caps 8% short at 14px and text 7-9% tall
#   at 16-20px), but in Medium-ExtraBold it closes counters and apertures at
#   many sizes (e, a, g, s, S, 3, 6, oe/ae), so legibility got worse.
# Override per build: make build TTFA_ARGS="-x 0 -a qsq"
TTFA_ARGS ?= -x 0 -a qss

# Per-font ttfautohint control files (sources/ttfautohint/<font name>.ctrl),
# for fixes that only some weights need, e.g. the bold i/j dot at 13-14px.
TTFA_CTRL = $(wildcard sources/ttfautohint/*.ctrl)

help:
	@echo "###"
	@echo "# Build targets for $(FAMILY)"
	@echo "###"
	@echo
	@echo "  make build:  Builds the fonts and places them in the fonts/ directory"
	@echo "  make test:   Tests the fonts with fontspector"
	@echo "  make proof:  Creates HTML proof documents in the proof/ directory"
	@echo "  make hinting-test:  Small-size static vs variable test page in out/hinting-test/"
	@echo "  make images: Creates PNG specimen images in the documentation/ directory"
	@echo

build: build.stamp

venv: venv/touchfile

customize: venv
	. venv/bin/activate; python3 scripts/customize.py

build.stamp: venv Makefile sources/config.yaml $(SOURCES) $(TTFA_CTRL) scripts/fix_fonts.py scripts/autohint_fonts.py scripts/make_webfonts.py
	rm -rf fonts
	(for config in sources/config*.yaml; do . venv/bin/activate; gftools builder $$config; done) && \
	. venv/bin/activate; find fonts -name "*.ttf" | xargs python3 scripts/fix_fonts.py && \
	{ [ -f "fonts/variable/Scoutie-Sans[wght].ttf" ] && mv "fonts/variable/Scoutie-Sans[wght].ttf" "fonts/variable/ScoutieSans[wght].ttf" || true; } && \
	{ [ -f "fonts/variable/Scoutie-Sans-Italic[wght].ttf" ] && mv "fonts/variable/Scoutie-Sans-Italic[wght].ttf" "fonts/variable/ScoutieSans-Italic[wght].ttf" || true; } && \
	python3 scripts/autohint_fonts.py --args "$(TTFA_ARGS)" --ctrl-dir sources/ttfautohint fonts/ttf/*.ttf && \
	python3 scripts/make_webfonts.py fonts && \
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

hinting-test: build.stamp
	rm -rf out/hinting-test && mkdir -p out/hinting-test/fonts
	cp scripts/hinting-test.html out/hinting-test/index.html
	cp fonts/webfonts/*.woff2 out/hinting-test/fonts/

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
