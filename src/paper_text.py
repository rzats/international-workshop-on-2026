# -*- coding: utf-8 -*-
"""The manuscript. Numbers are substituted from the computed results at build time."""

TITLE = ("Converting low-quality library scans into large-print editions "
         "with layout analysis and constraint-based reflow")

VENUE = ("SCIA-2026: International Workshop on Social Communication and Information "
         "Activity in Digital Humanities, December 10, 2026, Lviv, Ukraine")

AUTHORS = [
    dict(first="Rostyslav", last="Zatserkovnyi", marks="1,∗,†",
         email="zatserkovnyi.rostyslav@gmail.com", short="R. Zatserkovnyi",
         orcid="0000-0001-6991-2866"),
    dict(first="Roksoliana", last="Zatserkovna", marks="2,†",
         email="roksoliana.s.zatserkovna@lpnu.ua", short="R. Zatserkovna",
         orcid="0000-0003-1011-053X"),
]
AFFILIATIONS = [
    "Lviv University of Trade and Economics, 10 Tuhan-Baranovskyi Str., Lviv, 79008, Ukraine",
    "Lviv Polytechnic National University, 12 Stepan Bandera Str., Lviv, 79013, Ukraine",
]

KEYWORDS = ("large-print editions, low vision accessibility, document layout analysis, "
            "text reflow, OCR quality")

ABSTRACT = (
 "Public-domain scans in library repositories are normally published together with the OCR "
 "derivative that the repository's own pipeline produced, and that derivative is the cheapest "
 "route to a reflowable large-print edition for readers with low vision. It is also the "
 "riskiest: the derivatives were made by different engines over two decades, their word-level "
 "confidence values are not comparable between volumes, and reflowing them faithfully "
 "reproduces every recognition error at 18 pt. We describe a pipeline that decides, passage by "
 "passage, whether the recognised text is trustworthy enough to reflow, and keeps the remainder "
 "as magnified, deskewed images of the original lines, re-imposed to fit the new measure. Layout "
 "analysis strips running heads and folios and recovers headings and verse; a calibrated "
 "reliability model estimates the probability that each recognised token is wrong; a budgeted "
 "selection withdraws the least trustworthy passages from the reflowable layer; and a dynamic "
 "program paginates the mixed material under typographic constraints. On {NBOOKS} public-domain "
 "volumes ({SRCPAGES} scanned pages, {ALIGNEDM} million words aligned to clean e-texts as "
 "reference transcriptions), the reliability model ranks erroneous tokens better than the "
 "engines' own confidence in every volume (mean AUC {AUCM} against {AUCC}). Withdrawing {B10} of "
 "the running text removes {RED10}% of the errors a reader would otherwise meet, against "
 "{REDC10}% for confidence-based selection, at no cost in pages. Constrained pagination removes "
 "{VIOLRED}% of widows, orphans and stranded headings for {PAGEOVH}% more pages."
)


# Body. Each entry is (kind, payload). Kinds: h1, h2, p, p0 (no indent), ul, ol,
# fig, table, note.  {PLACEHOLDERS} are filled from the computed results.
BODY = [
("h1", "Introduction"),
("p0",
 "Library digitisation programmes have put tens of millions of scanned volumes within reach of "
 "anyone with a network connection. For a reader with low vision, however, a scanned page is "
 "not yet a readable book. The page image carries the type size of the original edition, and "
 "nineteenth-century trade printing is small relative to its page: shown whole on A4, only "
 "{NOPANFULL}% of the pages in our corpus reach 18 pt, the size at which large print is usually "
 "said to begin. Enlarging the image is possible in any viewer, but a page magnified to a "
 "comfortable size no longer fits the display, and the reader is left panning line by line. "
 "What is wanted instead is a genuine large-print edition: the same text, reset at 18 pt or "
 "more, on pages that can be read straight through."),
("p",
 "The material for such a reset edition is already there. Repositories publish, beside each "
 "scan, the output of their own optical character recognition, with word rectangles and "
 "per-word confidence, in the hOCR microformat [breuel2007] or a comparable schema "
 "[pletschacher2010]. Reflowing that text is cheap and produces output that is not merely "
 "larger but genuinely accessible: it can be resized further by the reader, read aloud by a "
 "screen reader, searched, and re-rendered on a phone. The difficulty is that the recognised "
 "text is wrong often enough to matter. Across our corpus {WERPCT}% of recognised words differ "
 "from the reference transcription, and in the worst volume the figure is {WERMAX}%. A reader "
 "of a facsimile meets the printer's text; a reader of an uncorrected reflow meets the "
 "recogniser's, with no way of telling which is which."),
("p",
 "This paper takes that tension as a design problem rather than a recognition problem. Instead "
 "of trying to correct the text, we decide where to trust it. Passages the system judges "
 "reliable are reflowed as real text at the target size. Passages it does not trust are kept as "
 "images of the original lines, magnified to the same target size and re-imposed so that each "
 "line still fits the new measure. The output is one document in which most of the content is "
 "reflowable and the rest is a faithful magnified facsimile, and in which the reader is never "
 "shown a confidently typeset misreading."),
("p",
 "The contributions are as follows. First, we show that the confidence values libraries publish "
 "with their OCR are not usable as a trust signal across a collection, because different "
 "engines and different vintages of the same engine put them on different scales, and we give a "
 "calibrated replacement built from engine-agnostic features that transfers to unseen volumes. "
 "Second, we formulate the choice between reflowed text and magnified facsimile as a selection "
 "under an explicit coverage budget, which gives a librarian a single dial between "
 "reflowability and residual error rather than an opaque threshold. Third, we compose the mixed "
 "material with optimal ragged-right line breaking and a pagination dynamic program that treats "
 "widows, orphans and stranded headings as hard constraints. Fourth, we report a reproducible "
 "evaluation on {NBOOKS} public-domain volumes from the Internet Archive, using clean Project "
 "Gutenberg e-texts of the same works as reference transcriptions, and we measure our own "
 "layout analysis honestly enough to change the design where it proved unreliable."),

("h1", "Related work"),
("h2", "Recognition quality in digitised collections"),
("p0",
 "That mass-digitised text is noisy, and that the noise propagates, is well established. Traub "
 "et al. [traub2015] quantified how recognition quality changes the outcome of archival search "
 "tasks; Hill and Hengchen [hill2019] showed that quantitative analyses of an eighteenth-century "
 "corpus shift measurably when run on dirty text; van Strien et al. [vanstrien2020] traced the "
 "effect through a series of language-processing tasks. Cordell [cordell2017] argues that "
 "recognition output should be read as a historical artefact in its own right rather than as a "
 "transparent window onto the page. The standard response is post-correction, surveyed by "
 "Nguyen et al. [nguyen2021] and benchmarked by the ICDAR competition series "
 "[chiron2017, kissos2016]; a research agenda for the area is set out by Smith and Cordell "
 "[smith2018]. Post-correction and the present work are complementary: correction reduces the "
 "error rate of the text layer, and what we do is decide how much of the remaining error a "
 "reader should be exposed to."),
("h2", "Layout analysis and reflow"),
("p0",
 "Document layout analysis is a mature field with comprehensive surveys [binmakhashen2019], "
 "standard ground-truth formats [pletschacher2010] and datasets [antonacopoulos2009], and "
 "modern learned toolkits [shen2021]. Detecting recurring page apparatus such as running heads "
 "is related to the structural tasks studied for tables of contents [lin2005]. Reflowing a "
 "scanned page onto a small display was studied two decades ago under the heading of document "
 "image reflow: the Paper-to-PDA line of work [breuel2002] segmented the page into line images "
 "and re-laid them out at a size suited to a handheld screen. Our re-imposition step is a "
 "descendant of that idea, applied for a different reason – not a small screen but a large type "
 "size – and mixed with reflowed text rather than used alone. The composition machinery is "
 "classical: optimal line breaking follows Knuth and Plass [knuth1981], and page breaking "
 "follows the dynamic-programming formulations of complex-document pagination "
 "[plass1983]."),
("h2", "Large print and low-vision reading"),
("p0",
 "Vision science gives the target a precise meaning. Legge and Bigelow [legge2011] review the "
 "relation between print size and reading speed and locate the fluent range well above the "
 "sizes used in trade printing. Studies of typeface legibility for readers with low vision "
 "[russellminda2007, arditi2005] and of type size for older readers [bernard2001] support the "
 "practical guidance that large print begins at about 18 pt, that generous leading and a "
 "moderate measure help, and that justified setting and hyphenation hinder. Letter spacing "
 "matters as well [chung2002]. Accessibility standards approach the same target from the "
 "digital side: WCAG 2.2 [wcag22] requires text to be resizable and reflowable, EPUB "
 "Accessibility 1.1 [epuba11] sets conformance requirements for digital publications, and the "
 "European Accessibility Act [eaa2019] makes such requirements binding for e-books placed on "
 "the Union market from 2025. The Marrakesh Treaty [marrakesh2013] gives authorised entities "
 "the right to make accessible-format copies of published works, which is precisely the "
 "activity this pipeline is meant to support. Work on production tooling for print-disabled "
 "readers has concentrated on braille transcription [zatserkovna2019]; large print has received "
 "less attention, although it serves a far larger population."),

("h1", "Design targets"),
("p0",
 "We fix the output format before describing the method, because the format determines what "
 "the layout engine has to achieve. Pages are A4 with 20 mm margins, giving a measure of "
 "{MEASURE} pt. Running text is set at 18 pt with 1.4 line spacing in Atkinson Hyperlegible, a "
 "typeface designed for readers with low vision. Setting is ragged right rather than justified, "
 "and hyphenation is disabled, both following the guidance summarised above. Captions and notes "
 "are set at the same size as the body. Headings are 22 pt. Composed body lines average "
 "{CPL} characters, which is inside the range usually recommended for large print."),
("p",
 "Two properties of the output are treated as non-negotiable. The first is typographic: no "
 "paragraph may be split so that a single line stands alone at the foot or the head of a page, "
 "and no heading may be separated from the text it introduces. A reader who has to work to "
 "follow the thread of a page is poorly served by a format whose whole purpose is to reduce "
 "effort. The second is that page apparatus belongs to the original page, not to the work: "
 "running heads, folios and catchwords must not be scattered through the reset text."),
("fig", ("pipeline",
 "Stages of the pipeline. Only the first stage touches the scanned page image; the layout, "
 "reliability and routing stages work from the published recognition output alone.")),

("h1", "Method"),
("h2", "Input"),
("p0",
 "The input to the pipeline is what a repository publishes: a page image per leaf and an hOCR "
 "file giving, for every page, a hierarchy of regions, paragraphs, lines and words, each with a "
 "bounding rectangle, and for every word a confidence value and an estimated type size "
 "[breuel2007]. No re-recognition is performed. This is deliberate: the derivatives already "
 "exist for millions of volumes, and a method that needs only them can be run over a collection "
 "at negligible cost."),
("h2", "Layout analysis"),
("p0",
 "Paragraphs are placed in reading order, with a projection over paragraph centres used to "
 "detect two-column pages, and are then assigned a role. Page apparatus is found by a "
 "whole-page test: the single-line paragraph at the very top or the very bottom of a page is "
 "furniture if its opening words recur across the volume, or if it consists only of a page "
 "number. Keying the recurrence test on the opening words rather than the whole line matters, "
 "because the tail of a running head is often the part the recogniser garbles, and a key built "
 "from the whole line differs on every page."),
("p",
 "Headings are recognised from type size, capitalisation and brevity. Verse needs a whole-page "
 "test of its own, because recognisers emit one paragraph per verse line and a paragraph-local "
 "rule cannot see a stanza: a page is verse when most of its lines stop well short of the right "
 "margin, its paragraphs are one or two lines long, a short line is not followed by an indented "
 "one, and the short lines do not begin with quotation marks. The last condition separates verse "
 "from rapid dialogue, which otherwise produces the same geometric signature. Verse paragraphs "
 "keep their original line division in the output instead of being reflowed, with a run-over "
 "indent where a verse line is too long for the new measure."),
("h2", "Reliability estimation"),
("p0",
 "Every recognised token receives an estimate of the probability that it differs from what is "
 "printed. The features fall into four groups. Lexical features record whether the normalised "
 "token, or a light morphological variant of it, appears in a period lexicon built from "
 "Webster's 1913 Unabridged and from clean e-texts disjoint from the evaluation corpus. Shape "
 "features record length, the proportion of non-alphanumeric characters, runs of punctuation, "
 "case transitions inside a word, and isolated one- or two-letter tokens that are not English "
 "short words. Geometric features record how far the line's type size and the token's height "
 "and aspect depart from the volume's median, and the token's vertical position on the page. "
 "Confidence features use the engine's value, but in three forms: the raw value, its z-score "
 "within the volume, and its rank percentile within the volume. Two neighbourhood features "
 "average the confidence percentile and lexicon membership of the surrounding tokens, which "
 "captures the tendency of recognition failures to cluster."),
("p",
 "A logistic model over these features is fitted and evaluated leave-one-volume-out, so that "
 "every reported number describes transfer to a volume the model has never seen. Within-volume "
 "normalisation is the component that makes transfer possible: the raw confidence scales differ "
 "so sharply between derivatives that a threshold tuned on one volume is meaningless on "
 "another. Calibration is assessed with the expected calibration error, in the manner usual for "
 "probability estimates [niculescu2005, guo2017], because the routing stage consumes "
 "probabilities rather than ranks."),
("h2", "Routing under a coverage budget"),
("p0",
 "Let a segment be a paragraph, with {NTOK} tokens and estimated expected error {EXPERR}. "
 "Routing chooses, for each segment, whether it is reflowed as text or kept as facsimile. "
 "Keeping a segment as facsimile removes its expected errors from the text layer, but also "
 "removes its words from the reflowable, screen-readable part of the edition. We therefore make "
 "reflowable coverage the budgeted resource: the operator specifies the fraction of running "
 "words that may be withdrawn, and the system withdraws segments in decreasing order of "
 "estimated error density until the budget is spent. This is the fractional-knapsack ordering "
 "and is optimal for the relaxed problem; with paragraph-sized items the integrality gap is "
 "negligible."),
("p",
 "Expressing the control as a coverage budget rather than a confidence threshold has a "
 "practical benefit beyond optimality. A threshold on a confidence value means something "
 "different in every volume, as Section {SECREL} shows; a coverage budget means the same thing "
 "everywhere, and it lets us compare selection rules at matched coverage, which is how the "
 "experiments below are organised."),
("h2", "Reflow and pagination"),
("p0",
 "Text segments are broken into lines by a Knuth–Plass dynamic program [knuth1981] in its "
 "ragged-right form: interword space is fixed, and the badness of a line is a cubic function of "
 "how far short of the measure it stops, so the optimisation evens out the right-hand edge "
 "instead of stretching word spaces. Hyphenation is disabled, and the last line of a paragraph "
 "is free."),
("p",
 "Pagination is a second dynamic program over the resulting stream of atomic items – text "
 "lines, facsimile strips and illustrations. The cost of a page is a constant plus a penalty "
 "for unused height, so that minimising cost minimises the page count and then prefers full "
 "pages. Breaks that would leave a paragraph's opening line alone at the foot of a page, carry "
 "its closing line alone to the next, strand a heading at a page foot, or separate a heading "
 "from the first two lines it introduces are charged a penalty large enough to act as a hard "
 "constraint. Because the constraint is expressed in the objective rather than as a filter, the "
 "program still returns a layout when a segment is physically too tall to satisfy it."),
("h2", "Re-imposition of facsimile lines"),
("p0",
 "A segment routed to facsimile is not pasted in as a block. Each source line is cut out "
 "separately and scaled so that its type reaches the target size; since the hOCR type size is "
 "reported in scan pixels, the scale factor for a line is simply the ratio of the target size "
 "to the reported size, and the strip's height in points follows from its rectangle. A strip "
 "wider than the measure is divided at an interword gap – the word rectangles give the gaps "
 "directly – and continued on the next strip with a run-over indent. Strips are atomic items "
 "for the pagination program, so a facsimile passage flows across a page break exactly as "
 "reflowed text does."),
("p",
 "Scans of bound volumes, and microfilm in particular, are rarely square to the page, and a "
 "rectangular crop of a sloping line catches the descenders of its neighbours. The baseline "
 "slope that the recogniser already reports for each line is used to rotate each strip upright "
 "before it is placed, which removes the artefact without any image analysis of our own. One "
 "further practical detail is that the order of pages in a published hOCR file does not always "
 "agree with the repository's own leaf numbering; the offset is recovered automatically by "
 "matching the aspect ratio of a few sample leaves against the page rectangles in the hOCR."),
]

BODY += [
("h1", "Evaluation"),
("h2", "Corpus"),
("p0",
 "The corpus is {NBOOKS} public-domain volumes from the Internet Archive, listed in Table 1, "
 "chosen so that each work also exists as a clean Project Gutenberg e-text and so that the set "
 "spans prose, illustrated prose and verse, printings from {YEARMIN} to {YEARMAX}, and three "
 "different recognition engines. One volume is a microfilm-derived scan, included deliberately "
 "as a worst-case source. Together the volumes comprise {SRCPAGES} scanned pages, "
 "{TOKENS} recognised tokens and {FIGS} illustration regions."),
("table", "corpus"),
("h2", "Reference transcriptions"),
("p0",
 "The e-text of the same work supplies the reference transcription. Aligning the two word "
 "streams labels every recognised token as correct, substituted or spurious. Alignment follows "
 "the anchor-based scheme used for automatic evaluation of book recognition [yalniz2011, "
 "feng2006]: five-gram sequences that occur exactly once in each stream are matched, a longest "
 "increasing subsequence gives a monotone chain of anchors, and the gaps between consecutive "
 "anchors are aligned with a sequence matcher. Line-final hyphens are joined before alignment, "
 "so that a word broken across two lines is compared as one word."),
("p",
 "Scanned volumes and e-texts do not agree on everything: a scan carries front matter, plates, "
 "advertisements and an editor's introduction that the e-text does not, and the two may "
 "represent different editions. A token is therefore scored only when it falls inside a gap "
 "between anchors that is short and of comparable length on both sides; long or lopsided gaps "
 "mean divergent content rather than recognition error and are left unscored. {ALIGNPCT}% of "
 "tokens are scorable under this rule, and the pooled word error over them is {WERPCT}% "
 "(95% CI {WERCI}), computed with the Wilson interval [wilson1927, brown2001] as all "
 "proportions in this paper are."),
("h2", "Measures"),
("p0",
 "Three quantities describe an edition. Residual error density is the number of erroneous "
 "recognised words that the edition presents as text, per thousand scorable words of the work; "
 "an all-facsimile edition scores zero by construction. Reflowable coverage is the fraction of "
 "running words delivered as text rather than as images, and stands for everything a text layer "
 "buys the reader: further magnification, screen reading, search, re-rendering. Extent is the "
 "number of A4 pages. We also report typographic violations per hundred pages and the "
 "root-mean-square raggedness of the right-hand edge over body lines."),
("h2", "Systems compared"),
("p0",
 "Five composition strategies are compared at full coverage. Magnify-and-tile crops each "
 "scanned page to its text block, magnifies it until the type reaches 18 pt and tiles the "
 "result across A4 pages; this is the baseline a page-image viewer effectively offers, and it "
 "is given every advantage. All-facsimile re-imposes every line as a magnified strip. "
 "Greedy-reflow sets all recognised text with first-fit line breaking and fills pages to "
 "capacity. Unconstrained Knuth–Plass replaces the line breaker only. Constrained reflow adds "
 "the pagination program."),
("p",
 "Four selection rules are then compared at matched coverage budgets of 2, 5, 10, 20 and 40%. "
 "All four withdraw segments through the same procedure and differ only in how they rank them: "
 "by the reliability model's mean predicted error probability; by the engine's own mean "
 "confidence, which is the obvious alternative; at random, which is the floor; and by the true "
 "error density measured against the reference transcription, which is the ceiling attainable "
 "by any ranking."),

("h1", "Results"),
("h2", "How far magnification alone goes"),
("p0",
 "Showing a scanned page whole on A4 reaches 18 pt on only {NOPANFULL}% of the pages in the "
 "corpus. Cropping away the original margins first is much more effective and gets "
 "{NOPANCROP}% of pages there, but the remainder is concentrated: in three volumes fewer than "
 "one page in ten reaches the target even after cropping. Tiling the magnified pages so that "
 "the target size is always met costs {MAGPAGES} pages, {MAGRATIO} times the extent of a "
 "reflowed edition of the same content and {MAGSRC} times the extent of the original volumes. "
 "Magnification alone is thus neither compact nor uniformly sufficient, quite apart from "
 "producing nothing a screen reader can use."),
("h2", "Layout analysis"),
("p0",
 "Removal of page apparatus can be checked without hand labelling, because running heads, "
 "folios and catchwords are printing apparatus that does not appear in the e-text of the work. "
 "Aligning the unfiltered token stream against the e-text shows that of the {FURNTOK} tokens "
 "the analysis calls furniture, only {FURNMATCH}% match the reference transcription (95% CI "
 "{FURNCI}), while {BODYMATCH}% of the tokens it keeps as body text do. In other words the "
 "filter discards almost nothing that belongs to the work."),
("p",
 "The finer roles are less trustworthy. Table 2 reports precision on a sample of twelve "
 "paragraphs per predicted class, drawn across all volumes and adjudicated by the authors "
 "against the scanned pages. Furniture and verse are reliable; heading detection confuses "
 "chapter titles with the running heads that escaped the furniture filter; and caption and "
 "footnote detection are poor, because the illustration regions the recognisers emit are "
 "over-generated and body text often sits next to one. That tokens labelled caption match the "
 "e-text almost as often as body text does (Table 2) corroborates the sampled verdict that most "
 "of them are body text. Because the sample is stratified by "
 "predicted class it measures per-class precision, not overall accuracy; furniture and body "
 "together account for {FBSHARE}% of all tokens."),
("p",
 "This measurement changed the design. An earlier version of the system set captions and "
 "footnotes two points smaller than the body, as a printed book would. Given the measured "
 "precision, that decision would have set misclassified body text below the large-print "
 "threshold on a non-trivial number of paragraphs, so captions and notes are now set at the "
 "body size and the caption and footnote labels are used only for ordering. The composition "
 "rules rely only on the distinctions the analysis gets right."),
("table", "roles"),
("h2", "Reliability estimation"),
("p0",
 "The confidence values published with the derivatives are not comparable across the "
 "collection. In one volume no token is assigned a confidence above 30 and the modal value is "
 "29; in another, produced by a recent Tesseract release, {BASKHIGH}% of tokens score 90 or "
 "more. Pooled over the corpus, ranking tokens by raw confidence gives an AUC of {POOLEDCONF} "
 "for the task of finding the erroneous ones, and replacing the raw value by its rank "
 "percentile within the volume raises this only to {POOLEDPCT}: the problem is not merely one "
 "of scale."),
("p",
 "The full model, evaluated leave-one-volume-out, reaches a mean AUC of {AUCM} (SD {AUCMSD}) "
 "against {AUCC} (SD {AUCCSD}) for raw confidence, and is better on all {NBOOKS} volumes "
 "(sign test, p = {SIGNP}). Figure 2 shows the per-volume comparison. The margin is largest "
 "exactly where it is most useful: on volumes whose confidence values carry almost no signal, "
 "such as Walden (AUC {WALDENC} from confidence, {WALDENM} from the model) and Moby-Dick "
 "({MOBYC} against {MOBYM}). The hardest volume for both is The Time Machine, which has the "
 "highest error rate in the corpus and the least informative confidence values. Mean expected "
 "calibration error is {ECE}; Figure 3 shows the pooled reliability diagram, which tracks the "
 "diagonal across two orders of magnitude with a mild tendency to over-predict at the low end "
 "and under-predict at the high end."),
("fig", ("auc",
 "Ranking quality per volume for the task of identifying an erroneous recognised token. Circles: "
 "the reliability model, evaluated leave-one-volume-out. Squares: the confidence value published "
 "with the derivative. The asterisk marks the microfilm-derived scan.")),
("fig", ("calibration",
 "Pooled reliability diagram for the leave-one-volume-out predictions, on logarithmic axes. "
 "Confidence intervals are smaller than the markers.")),
("h2", "Line breaking and pagination"),
("p0",
 "Table 3 gives the composition strategies at full coverage. Greedy line breaking and "
 "Knuth–Plass produce the same number of pages, which is expected when hyphenation is disabled "
 "and paragraphs are long; the difference is in the right-hand edge, whose root-mean-square "
 "raggedness falls from {RAGG} to {RAGKP}, a reduction of {RAGRED}%. The pagination program is "
 "where the substantive difference lies: it removes {VIOLRED}% of widows, orphans and stranded "
 "headings, from {VIOLG} occurrences to {VIOLC}, at a cost of {PAGEOVH}% more pages. No widows "
 "and no orphans survive; the residual {VIOLC} are all stranded headings on display pages – "
 "title pages, half-titles and publishers' advertisements – where every line is classified as a "
 "heading and there is no following body text for the keep-with-next rule to attach to. "
 "All-facsimile costs {FACOVH}% more pages than constrained reflow, which is the price of "
 "carrying line images rather than reset type."),
("table", "composition"),
("h2", "The coverage and error trade-off"),
("p0",
 "Table 4 and Figure 4 give the central result. Reflowing everything exposes {RED0} erroneous "
 "words per thousand. Withdrawing {B10} of the running text on the reliability model's "
 "ranking brings this to {RED10V}, a reduction of {RED10}%, and closes {GAP10}% of the gap "
 "between reflowing everything and the best any ranking could do. The same budget spent on the "
 "engine's confidence reaches only {REDC10V}, a reduction of {REDC10}%, and spent at random "
 "{REDR10V}. At a 40% "
 "budget the model reaches {RED40V} against {REDC40V} for confidence and {REDR40V} for random, "
 "with the oracle at {REDO40V}."),
("p",
 "The page cost of this is small and, at moderate budgets, negative. At a 10% budget the "
 "edition is {PAGE10}% shorter than the all-text edition: the total vertical extent of the "
 "content falls by {HEIGHT10}%, because in most volumes a magnified image of a short source "
 "line occupies slightly less height than the same words reflowed with their own line spacing. "
 "Only at a 40% budget does the extent rise, by {PAGE40}%. The operator is therefore "
 "trading reflowability against residual error, not pages against error, which is the honest "
 "way to present the choice."),
("table", "routing"),
("fig", ("tradeoff",
 "Residual error density against reflowable coverage, pooled over the corpus. Each curve spends "
 "the same coverage budget and differs only in which passages it withdraws from the reflowable "
 "layer. Error bars are Wilson 95% intervals.")),
("p",
 "Per volume (Table 5) the reliability model beats the confidence ranking in {WINS} of the "
 "{NBOOKS} volumes at the 10% operating point; the paired sign test over volumes is not "
 "significant (p = {WINP}), although the pooled difference is decisive, the Wilson intervals "
 "{CI10M} and {CI10C} being disjoint. The four exceptions are informative. A Christmas Carol is the smallest volume in the corpus "
 "({CAROLTOK} scorable tokens) and the only one in which random withdrawal beats both rankings, "
 "which is what one expects when the error is spread evenly rather than concentrated. Leaves of "
 "Grass and Tom Sawyer are the two volumes in which paragraph segmentation is weakest – "
 "free verse in the first, dialogue in the second – so paragraph-level ranking has less to work "
 "with; in Dracula the two rankings are level to within 0.1 per thousand. The microfilm volume is the clearest win ({BASKBASE} to {BASKMODEL} against {BASKCONF}), "
 "but also the one case where the page cost is real: its line rectangles are tall relative to "
 "the type, so its facsimile strips are expensive, and the extent grows by {BASKPAGES}%."),
("table", "perbook"),
("h2", "A composed page"),
("p0",
 "Figure 5 shows one page of the microfilm volume beside the page of the large-print edition "
 "that carries the same text. The running head and the folio have gone; three paragraphs are "
 "reflowed at 18 pt; and two passages that the reliability model distrusted are kept as "
 "magnified, deskewed strips of the original setting, each fitted to the new measure. A reader "
 "meets the printer's letterforms exactly where the recogniser was least trustworthy, and reset "
 "type everywhere else."),
("fig", ("example",
 "Left: a page of the microfilm-derived scan of The Hound of the Baskervilles. Right: the "
 "corresponding page of the large-print edition produced at a 10% coverage budget. The shaded "
 "lines are magnified facsimile strips of the original setting; the rest is reflowed at 18 pt.")),

("h1", "Discussion and limitations"),
("p0",
 "The result that matters practically is that the confidence values libraries publish are not, "
 "by themselves, a usable trust signal across a collection, and that a small model over "
 "features any consumer of hOCR already has does much better and transfers to unseen volumes. "
 "This is a modest claim technically and a consequential one operationally: a production "
 "pipeline that thresholds on published confidence will behave differently on every volume it "
 "meets, in ways its operators cannot see."),
("p",
 "Several limitations bound the evidence. The corpus is English-language literary prose and "
 "verse from a single repository; scholarly editions with dense apparatus, newspapers, and "
 "non-Latin scripts are untested, and the lexical features in particular would need rebuilding "
 "for another language. Reference transcriptions come from e-texts of the same work rather than "
 "of the same printing, which is why a tenth of tokens is left unscored; the unscored material "
 "is front matter and divergent editions, which is precisely the material a large-print edition "
 "would also contain, so the reported error rates describe the alignable body of the work "
 "rather than the whole volume. Reflowable coverage is a proxy for accessibility value and "
 "weights all words equally, whereas a reader would rather lose a page of advertisements than a "
 "page of the novel. Most importantly, no reader has yet been involved: the case that the "
 "hybrid output is preferable to either extreme rests on the argument that exposed recognition "
 "errors are harmful and reflowability is valuable, not on measured reading performance. A "
 "study with low-vision readers, measuring reading speed and comprehension across the operating "
 "curve, is the natural next step and would also give the coverage budget an empirical setting "
 "rather than an operator's guess; instruments for assessing how usable an adapted edition is "
 "to such readers already exist [zatserkovnyi2023] and could be applied at several points along "
 "the curve."),
("p",
 "Two engineering limitations are worth naming. Facsimile strips are images and carry no text "
 "layer, so the passages the system distrusts are also the passages a screen reader cannot "
 "voice; attaching the low-confidence recognised text to the strip as alternative text would "
 "recover that at the cost of reintroducing the error into the speech channel, and the right "
 "trade-off there is not obvious. And the layout analysis is rule-based; a learned segmenter "
 "[shen2021] would very likely repair the caption and footnote classes that we measured and "
 "then chose not to rely on. A third is that the type size a derivative reports for a line is "
 "engine-dependent and is not always a font size, so the magnification applied to a facsimile "
 "strip reaches the target only approximately; a measurement of x-height on the page image "
 "itself would make the target exact at the cost of touching the image."),

("h1", "Conclusion"),
("p0",
 "Large-print editions of digitised books can be produced from the recognition derivatives "
 "libraries already publish, without re-recognising anything and without asking a reader to "
 "choose between a faithful facsimile they must pan across and a reflowable text full of "
 "invisible errors. The pipeline described here decides passage by passage which of the two to "
 "use, controls that decision with a coverage budget that means the same thing in every volume, "
 "and composes the mixed material under typographic constraints that a reader with low vision "
 "has good reason to expect. On {NBOOKS} volumes, withdrawing a tenth of the running text "
 "removes {RED10}% of the errors a reader would otherwise meet, at no cost in pages. The code, "
 "the corpus manifest and every number in this paper are available at "
 "https://github.com/rzats/international-workshop-on-2026."),
]
