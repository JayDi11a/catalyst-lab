TEX = pdflatex
BIB = bibtex
SRC = main

all: $(SRC).pdf

$(SRC).pdf: $(SRC).tex references.bib
	$(TEX) $(SRC)
	$(BIB) $(SRC)
	$(TEX) $(SRC)
	$(TEX) $(SRC)

clean:
	rm -f *.aux *.log *.bbl *.blg *.out *.pdf *.fls *.fdb_latexmk *.synctex.gz

.PHONY: all clean
