# Two-edition cross-reference index

The request contains standard and large_print (two edition configurations), a common document and notes. Each configuration supplies page_width, page_height, float_gap and max_passes. notes contains a notes array of {id,height}; document contains a blocks array. Paragraphs have {kind:"paragraph",id,words}, where each word has text or ref, plus an optional note ID. Figures have {kind:"figure",id,width,height} and attach to the following paragraph. All references, figure dimensions and note IDs are valid.

Both editions use the following rules.

Begin each reference word with a page-number guess of 1 for every block. Its rendered token is `p` followed by the decimal guess, e.g. `p12`. A text word renders exactly as given. Each character counts as one column. Join words on a line with one ASCII space. Greedily append the next word if it fits; otherwise finish the current line and start the next. A word that cannot fit an empty line at its applicable width yields `UNSAT/WORD_TOO_WIDE`.

For the paragraph following a figure, its first `figure.height` lines have width `page_width - figure.width - float_gap`; later lines use full `page_width`. A figure's height is measured in body rows. It is anchored to the page carrying the paragraph's first line. The first fragment must include at least `min(figure.height,total paragraph lines)` lines; if the entire paragraph has fewer lines than figure height, the difference is padding charged on its page. The figure never extends onto another page. A paragraph without figure uses full width throughout.

Each wrapped line reports `{block,line,text,width,notes,refs}`. `line` is zero-based within the paragraph; `width` is rendered text length; `notes` is sorted unique note IDs from words on that line; `refs` is in word order with rows `{word,target,text}` for reference words. Empty lists appear explicitly.

## Greedy pagination with footnotes and orphan/widow rule

Start page 1. Process blocks in input order; a figure and following paragraph are one section. For a paragraph's remaining lines, choose the **largest prefix** that fits the current page. Fit cost is prefix line count, plus any figure padding on its first fragment, plus heights of notes newly introduced to that page. `used_rows` includes all those charges. A split is legal only if both the fragment placed now and the remaining paragraph each have at least two lines. A one-line or three-line paragraph therefore stays together. If no legal prefix fits a nonempty page, start a new page and retry; if none fits an empty page, yield `UNSAT/PAGE_CAPACITY`. After a legal split, start a new page. Figure width affects line wrapping before pagination. Footnote row charges affect the split; neither can be ignored when page numbers are derived.

For each page, `body` concatenates assigned lines in order. `figures` lists figure rows `{id,paragraph,width,height}` anchored to that page; `footnotes` lists sorted note IDs charged on the page. `number` starts at 1; `used_rows` is exact body rows + first-fragment figure pad + note heights. `anchors` maps every paragraph and figure ID to its starting page.

## Iteration, stability and no solution

At every pass, wrap and paginate using current guesses. Append an `anchors` map sorted by key to `history`, and let the resulting anchors be the next guesses. If *all* resulting pages equal the guesses, return `STABLE` immediately. Before running a pass, if the ordered guess tuple was previously used without convergence, return `UNSTABLE/CYCLE`. If `max_passes` passes finish without convergence, return `UNSTABLE/PASS_LIMIT`. `passes` counts actual layout attempts, including a failed capacity/width pass. An `UNSAT` result has empty `pages`/`anchors` and retains only successful prior history. `UNSTABLE` returns the pages/anchors from its latest completed pass.

Each edition report is exactly `{status,reason,passes,history,pages,anchors}`. `reason` is null for `STABLE`; `WORD_TOO_WIDE` or `PAGE_CAPACITY` for `UNSAT`; `CYCLE` or `PASS_LIMIT` for `UNSTABLE`. `pages` are in page order with exactly `{number,body,figures,footnotes,used_rows}`. `history` contains the per-pass anchor maps, in pass order.

Return {standard,large_print,index} with the two edition reports. If both editions are STABLE, index maps every block ID to [standard starting page, large_print starting page]. In all other cases index is null, even if provisional anchor maps are available. The public example shows the nested records.
