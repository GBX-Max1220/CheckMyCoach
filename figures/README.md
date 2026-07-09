# Paper Figures

## Compilation

Each `.tex` file is a standalone TikZ diagram. Compile to PDF:

```bash
cd figures
pdflatex fig1_pipeline.tex
pdflatex fig2_overview.tex
pdflatex fig3_ucs_engine.tex
```

Requires `pgf` (TikZ) — included in standard LaTeX distributions (TeX Live, MiKTeX).

## Files

| File | Description | Ref in Paper |
|------|-------------|-------------|
| `fig1_pipeline.tex` | CheckMyCoach four-stage pipeline architecture | Figure~\ref{fig:pipeline} |
| `fig2_overview.tex` | Research framework overview (3 contributions) | Figure~\ref{fig:overview} |
| `fig3_ucs_engine.tex` | UCS Engine four-stage classification pipeline | Figure~\ref{fig:ucs_engine} |

## Output

Compiled PDFs are referenced in paper.tex via `\includegraphics{figures/fig*.pdf}`.
