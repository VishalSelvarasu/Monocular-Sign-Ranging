"""Build the Monocular Sign Ranging project report.

Run from the repo root. If figures/*.png exist they are embedded;
otherwise the document builds text-only and notes the omission.

    python tools/build_report.py
"""
import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                TableStyle, PageBreak, Image, KeepTogether)

OUT = "Monocular_Sign_Ranging_Report.pdf"
FIGDIR = "figures"

INK = colors.HexColor("#1a1a1a")
ACCENT = colors.HexColor("#1f4e79")
RULE = colors.HexColor("#c8c8c8")
BAND = colors.HexColor("#eef2f6")
GREY = colors.HexColor("#5a5a5a")

ss = getSampleStyleSheet()

H1 = ParagraphStyle("H1", parent=ss["Heading1"], fontName="Helvetica-Bold",
                    fontSize=15, leading=19, textColor=ACCENT,
                    spaceBefore=16, spaceAfter=7)
H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontName="Helvetica-Bold",
                    fontSize=11.5, leading=15, textColor=INK,
                    spaceBefore=11, spaceAfter=4)
H3 = ParagraphStyle("H3", parent=ss["Heading3"], fontName="Helvetica-Oblique",
                    fontSize=10, leading=13, textColor=GREY,
                    spaceBefore=8, spaceAfter=3)
BODY = ParagraphStyle("BODY", parent=ss["BodyText"], fontName="Helvetica",
                      fontSize=9.4, leading=13.6, textColor=INK,
                      alignment=TA_LEFT, spaceAfter=6)
BULLET = ParagraphStyle("BULLET", parent=BODY, leftIndent=13,
                        bulletIndent=3, spaceAfter=3)
CODE = ParagraphStyle("CODE", parent=BODY, fontName="Courier", fontSize=8.2,
                      leading=11.2, leftIndent=9, spaceBefore=3, spaceAfter=7,
                      textColor=colors.HexColor("#243447"))
EQ = ParagraphStyle("EQ", parent=BODY, fontName="Courier-Bold", fontSize=10,
                    leading=14, leftIndent=14, spaceBefore=5, spaceAfter=8,
                    textColor=ACCENT)
CAP = ParagraphStyle("CAP", parent=BODY, fontSize=8.2, leading=11,
                     textColor=GREY, spaceBefore=2, spaceAfter=10)
TITLE = ParagraphStyle("TITLE", parent=ss["Title"], fontName="Helvetica-Bold",
                       fontSize=23, leading=27, textColor=ACCENT,
                       spaceAfter=4)
SUB = ParagraphStyle("SUB", parent=BODY, fontSize=11.5, leading=15,
                     textColor=GREY, spaceAfter=20)

S = []


def p(t, st=BODY):
    S.append(Paragraph(t, st))


def h1(t):
    S.append(Paragraph(t, H1))


def h2(t):
    S.append(Paragraph(t, H2))


def h3(t):
    S.append(Paragraph(t, H3))


def eq(t):
    S.append(Paragraph(t, EQ))


def code(t):
    S.append(Paragraph(t.replace("\n", "<br/>").replace(" ", "&nbsp;"), CODE))


def bullets(items):
    for i in items:
        S.append(Paragraph(i, BULLET, bulletText="\u2022"))
    S.append(Spacer(1, 5))


def gap(h=7):
    S.append(Spacer(1, h))


def table(rows, widths=None, align_right_from=1, highlight=None):
    data = [[Paragraph(f"<b>{c}</b>" if r == 0 else str(c),
                       ParagraphStyle("t", parent=BODY, fontSize=8.4,
                                      leading=11, spaceAfter=0,
                                      textColor=colors.white if r == 0 else INK))
             for c in row] for r, row in enumerate(rows)]
    t = Table(data, colWidths=widths, hAlign="LEFT", repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, RULE),
        ("ALIGN", (align_right_from, 1), (-1, -1), "RIGHT"),
    ]
    for r in range(1, len(rows)):
        if r % 2 == 0:
            style.append(("BACKGROUND", (0, r), (-1, r), BAND))
    if highlight:
        for r in highlight:
            style.append(("BACKGROUND", (0, r), (-1, r),
                          colors.HexColor("#fff4d6")))
    t.setStyle(TableStyle(style))
    S.append(t)
    gap(9)


def figure(name, caption, width=155*mm):
    path = os.path.join(FIGDIR, name)
    if not os.path.exists(path):
        p(f"<i>[figure {name} not found; run tools/figures.py first]</i>", CAP)
        return
    from PIL import Image as PILImage
    w, h = PILImage.open(path).size
    img = Image(path, width=width, height=width * h / w)
    S.append(KeepTogether([img, Paragraph(caption, CAP)]))


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(GREY)
    canvas.drawString(20*mm, 12*mm, "Monocular Sign Ranging")
    canvas.drawRightString(190*mm, 12*mm, f"{doc.page}")
    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.4)
    canvas.line(20*mm, 15*mm, 190*mm, 15*mm)
    canvas.restoreState()


# ============================================================ TITLE
p("Monocular Sign Ranging", TITLE)
p("Estimating traffic-sign distance from a single camera image, and "
  "measuring what a detector costs when it replaces ground-truth boxes",
  SUB)

table([
    ["Item", "Value"],
    ["Task", "Metric distance to traffic signs from one RGB image"],
    ["Reference", "Cityscapes stereo disparity"],
    ["Detector", "YOLO11s, single class, imgsz 1280"],
    ["Headline", "+/-24% error, 74% coverage, 18-64 m"],
    ["Precision", "0.73 to 0.83 (bounded, not exact)"],
    ["Evaluation", "Cityscapes val, held out from everything fitted"],
], widths=[35*mm, 120*mm], align_right_from=9)

h2("What this document is")
p("The repository README states the result. This report states how it was "
  "reached: the reasoning behind each design decision, the intermediate "
  "measurements that never made it into the README, the three validation "
  "errors caught during development, and a walkthrough of every code file. "
  "It is the long version, written so that the work can be reconstructed "
  "or challenged by someone who was not present for it.")

# ============================================================ AIM
h1("1. Aim")

p("The aim is to answer one question from a single camera frame: how far "
  "away is that traffic sign, in metres.")

p("Metres matter. A driver assistance system that outputs a distance "
  "category rather than a distance cannot be reasoned about downstream. If "
  "a sign is reported as <i>near</i>, the planner cannot decide when to act "
  "on it. It also cannot compare the current frame with the last one, which "
  "means no tracking, no smoothing, and no way to tell an approaching sign "
  "from a stationary artefact.")

p("A second requirement follows from the first: the estimate must be "
  "comparable across frames. A number that means 40 m in one image and 80 m "
  "in the next is not a measurement, whatever units it carries.")

h2("Scope")
p("This is a perception component, not a system. There is no tracking, no "
  "temporal filtering, no planner, and no vehicle. The deliverable is a "
  "characterised instrument: an estimator with a measured error "
  "distribution, a stated operating envelope, and a known failure mode.")

# ============================================================ PATH
h1("2. The path taken")

h2("2.1 The original plan, and why it was abandoned")

p("The project began as a GTSDB traffic-sign detector combined with Depth "
  "Anything V2 for monocular depth, producing three output categories: "
  "near, mid, and far.")

p("The reasoning at the time was that Depth Anything V2 predicts "
  "<i>relative</i> depth, so honest reporting meant discretising into "
  "ordered bins rather than claiming metres. That reasoning contained a "
  "factual error and a design error.")

h3("The factual error")
p("Depth Anything V2 ships metric-depth variants fine-tuned on Virtual "
  "KITTI for outdoor scenes. Relative-only output was never a constraint "
  "the model imposed; it was a choice, justified after the fact by a "
  "limitation that does not exist.")

h3("The design error, which is the fatal one")
p("Relative depth is normalised <b>per image</b>. The same predicted value "
  "carries different physical meaning in different frames. A sign at 30 m "
  "on an open road and a sign at 8 m in a tight urban scene can both "
  "normalise to the same value, so a <i>near</i> classification in one "
  "frame may be physically further away than a <i>mid</i> in another.")

p("This fails the cross-frame comparability requirement outright. The bin "
  "boundaries move with the background. That is not an imprecise "
  "measurement; it is not a measurement.")

h2("2.2 What replaced it")

p("German traffic signs are manufactured to standard dimensions specified "
  "in the Verkehrszeichenkatalog. Round Vorschriftzeichen come in nominal "
  "sizes around 420, 600 and 750 mm; triangular Gefahrzeichen at 630, 900 "
  "and 1260 mm. If the physical size is known, distance follows from "
  "similar triangles:")

eq("Z  =  f_y * H_real / h_px")

table([
    ["Symbol", "Meaning", "Source"],
    ["Z", "Estimated distance, metres", "output"],
    ["f_y", "Vertical focal length, pixels", "camera calibration"],
    ["H_real", "Assumed physical sign height, metres", "size prior"],
    ["h_px", "Observed sign box height, pixels", "detector or annotation"],
], widths=[22*mm, 78*mm, 55*mm], align_right_from=9)

p("Three properties make this preferable to a learned depth model for this "
  "specific task. The output is in metres by construction. The error "
  "sources are enumerable and separable: calibration, box height, and size "
  "assumption. And the error propagation is differentiable in closed form, "
  "so the accuracy can be predicted rather than only observed:")

eq("dZ / Z  =  - dh / h")

p("A two-pixel error on a twenty-pixel box is a ten percent distance "
  "error; the same two pixels on an eighty-pixel box is 2.5 percent. That "
  "relationship is the reason every result in this project is stratified by "
  "box height rather than averaged.")

h2("2.3 Why validation moved from GTSDB to Cityscapes")

p("GTSDB is a genuine traffic-sign detection benchmark, but it publishes "
  "neither camera intrinsics nor any depth ground truth. Without f_y there "
  "is no way to compute Z, and without reference distance there is no way "
  "to check it. The geometric method could have been implemented on GTSDB "
  "and never validated.")

p("Cityscapes supplies all three missing pieces:")
bullets([
    "<b>camera.json</b> per frame, giving f_x, f_y, and the stereo baseline",
    "<b>disparity PNGs</b>, 16-bit, from which metric depth is recoverable",
    "<b>gtFine polygons</b>, including a <font face='Courier'>traffic sign</font> class",
])

p("The disparity decode used throughout is the documented Cityscapes "
  "convention:")
code("d = (p - 1) / 256      for p > 0        # p = 0 marks invalid\n"
     "Z = baseline * f_x / d")

p("with f_x approximately 2262 px at 2048x1024 and baseline approximately "
  "0.209 m.")

p("The cost of this move is that Cityscapes annotates every sign with a "
  "single semantic class and no type. That decision echoes through the "
  "entire project: without sign type, no size class can be inferred, and "
  "the size prior has to stay fixed. Section 9 returns to this.")

h2("2.4 Build order was deliberately inverted")

p("The obvious order is: train detector, add distance, validate. That order "
  "was rejected.")

p("If the detector is built first and the distances come out wrong, there "
  "is no way to attribute the failure. Bad boxes, wrong size assumption, "
  "and wrong intrinsics all produce the same symptom. Each stage would have "
  "to be debugged against a moving target.")

p("Building it backwards isolates one variable at a time:")

table([
    ["Stage", "Question", "Variables in play"],
    ["0", "Is stereo depth usable as reference?", "reference only"],
    ["0b", "Is that reference contaminated?", "reference only"],
    ["1", "What physical size should be assumed?", "reference + geometry"],
    ["2", "How accurate is geometry alone?", "+ size prior"],
    ["3", "Can signs be detected at all?", "detector only"],
    ["4", "What does detection cost the estimate?", "everything"],
], widths=[13*mm, 78*mm, 64*mm], align_right_from=9)

p("Each stage validates before the next adds noise. It also meant the "
  "project had a defensible result after Stage 2, before any GPU time was "
  "spent.")

S.append(PageBreak())

# ============================================================ STAGE 0
h1("3. Stage 0: is the reference measurement usable?")

p("Nothing can be built on a reference that has not been checked. Stage 0 "
  "answers two questions with code, before any modelling.")

h2("3.1 Coverage")

p("Across the first five Cityscapes train cities:")

table([
    ["Metric", "Value"],
    ["Images", "825"],
    ["Annotated sign polygons", "5,512"],
    ["Signs with usable reference distance", "4,863 (88%)"],
    ["Median disparity fill inside sign boxes", "1.00"],
], widths=[95*mm, 40*mm])

p("Sign short side: p10 = 10 px, median = 22 px, p90 = 61 px.<br/>"
  "Reference distance: p10 = 19 m, median = 48 m, p90 = 97 m.")

p("Two observations shaped everything downstream. First, the median sign is "
  "22 pixels on its short side, which is small enough that detector "
  "resolution becomes a first-order concern rather than a tuning detail. "
  "Second, the median reference distance is 48 m, meaning the dataset is "
  "dominated by far, small signs, which is exactly the regime where "
  "dZ/Z = dh/h predicts the worst accuracy.")

h2("3.2 The disparity fill result, and why it was suspicious")

p("A median disparity fill of exactly 1.00 across 5,512 boxes means every "
  "pixel inside every sign box carried a valid disparity value. Real stereo "
  "matching on thin structures against sky does not behave that way. The "
  "likely explanation is that Cityscapes disparity is SGM-derived and then "
  "hole-filled, so a pixel reported as valid inside a thin sign box may "
  "have been interpolated from the pole or the building behind it.")

p("If true, the ground truth would be partly synthetic in precisely the "
  "places that matter most. That warranted a separate test.")

h2("3.3 Stage 0b: testing for background bleed")

p("The test compares two estimators of the same quantity. Median disparity "
  "inside the box is what the pipeline uses. The 90th percentile "
  "corresponds to the nearest surface inside the box, so it is less "
  "susceptible to background pixels, which are further away and therefore "
  "have lower disparity.")

p("If background bleed were significant, the gap between the two would be "
  "large and would grow as boxes shrink, because a small box has "
  "proportionally more boundary.")

table([
    ["Short side (px)", "n", "median vs p90 gap", "median Z (m)"],
    ["0-15", "1,296", "3.9%", "72.9"],
    ["15-30", "1,951", "3.7%", "54.3"],
    ["30-60", "1,108", "2.7%", "32.2"],
    ["60+", "508", "2.0%", "19.5"],
], widths=[35*mm, 25*mm, 45*mm, 35*mm])

p("<b>The prediction failed.</b> The gap is 2 to 4 percent and it "
  "<i>shrinks</i> as boxes grow, which is the opposite of the bleed "
  "signature and too small to matter. The observed pattern is consistent "
  "with mild plate tilt, genuine depth variation across the sign surface, "
  "and annotation boundaries running slightly wide.")

p("Median disparity was retained as the reference. This is a negative "
  "result and it took an hour, but every subsequent number rests on it.")

# ============================================================ STAGE 1
h1("4. Stage 1: recovering the physical size prior")

p("The ranging equation needs H_real, and there is no way to look it up "
  "per sign because Cityscapes does not record sign type. The prior has to "
  "be derived from the data.")

h2("4.1 Method")

p("Inverting the equation turns each annotated sign with a known reference "
  "distance into a measurement of its own physical height:")

eq("H  =  Z * h_px / f_y")

p("Three filters were applied before reading anything into the "
  "distribution, and each has a reason:")

table([
    ["Filter", "Reason"],
    ["h_px >= 30 px",
     "Small boxes carry roughly 10% distance noise, which smears any real "
     "clustering into a single blur. Peaks are only visible on "
     "well-resolved signs."],
    ["|w/h - 1| < 0.25",
     "Cityscapes includes rectangular direction signs and Zusatzzeichen, "
     "which have no standard height. Near-square isolates round "
     "Vorschriftzeichen and triangular Gefahrzeichen."],
    ["f_y, not f_x",
     "A vertical extent is being inverted, so the vertical focal length is "
     "the correct one. The two are near-identical in Cityscapes, but using "
     "f_x here would be wrong."],
], widths=[38*mm, 117*mm], align_right_from=9)

h2("4.2 Result")

figure("size_prior.png",
       "Implied physical sign height, recovered by inverting the ranging "
       "equation against stereo depth. 991 near-square train signs at least "
       "30 px high.")

table([
    ["Percentile", "Implied height (train, n=991)", "Val (n=727)"],
    ["p10", "424 mm", "414 mm"],
    ["p25", "574 mm", "499 mm"],
    ["p50", "651 mm", "641 mm"],
    ["p75", "842 mm", "830 mm"],
    ["p90", "1227 mm", "1050 mm"],
], widths=[28*mm, 62*mm, 40*mm])

p("The dominant peak sits at 600 to 700 mm with 261 of 991 signs. That "
  "range contains VzKat Groesse 2 for round signs (600 mm) and the "
  "triangular Gefahrzeichen at 630 mm, which are not separable at this "
  "resolution. A secondary bump at 400 to 500 mm holds 130 signs and is "
  "consistent with Groesse 1 at 420 mm. A tail above 1500 mm holds 42 "
  "signs and is physically impossible for a single standard plate; these "
  "are most likely multi-plate assemblies annotated as one polygon whose "
  "bounding box happens to be near-square.")

h2("4.3 Why this matters more than the prior itself")

p("The peak landing on a documented standard is independent confirmation "
  "that the entire measurement chain is correct: disparity decode, "
  "baseline, focal length, and polygon extents. If any of those were wrong "
  "the peak would sit at an arbitrary value. This was not the purpose of "
  "the experiment, and it is the strongest validation the project "
  "produced.")

h2("4.4 The prior, and the ceiling it imposes")

p("The prior adopted is <b>650 mm</b>, the median rather than the modal "
  "600 mm. The median minimises error over the actual distribution the "
  "system will be scored against, not over an idealised one.")

p("The interquartile range is 574 to 842 mm. Against a 650 mm prior that "
  "is -12% to +30%. This is a hard floor:")

p("<b>Before any pixel is measured, before any detector exists, the "
  "distance estimate carries roughly plus or minus 25 percent "
  "irreducible bias from not knowing which size class a sign belongs to.</b>")

p("No amount of detector accuracy or geometric care reduces it. Only "
  "classifying sign type does.")

h2("4.5 Does the prior transfer?")

p("Re-deriving on the held-out val split gives 641 mm against 651 mm, a "
  "1.5 percent difference, so the central tendency transfers. The "
  "distributions differ in shape rather than centre: 17.7 percent of clean "
  "val signs fall in the 400 to 500 mm bin against 13.1 percent on train. "
  "Val is more strongly bimodal between Groesse 1 and Groesse 2, so a "
  "fixed prior is wrong more often there, in both directions.")

p("The prior was <b>not</b> re-fitted on val. Doing so would be fitting "
  "the test set.")

S.append(PageBreak())

# ============================================================ STAGE 2
h1("5. Stage 2: geometry alone, with perfect boxes")

p("Stage 2 applies the prior to ground-truth annotation boxes, with no "
  "detector involved. This isolates the geometric estimator: whatever error "
  "appears here is attributable to the size prior and the reference, "
  "nothing else.")

h2("5.1 Result on the held-out split")

table([
    ["Box h (px)", "n", "median Z_true", "bias", "p25", "p75", "median |err|"],
    ["15-30", "730", "63.9 m", "+9.0%", "-12%", "+43%", "23.7%"],
    ["30-60", "527", "36.0 m", "+3.1%", "-20%", "+38%", "24.7%"],
    ["60+", "223", "18.4 m", "-13.3%", "-28%", "+11%", "23.5%"],
], widths=[23*mm, 16*mm, 27*mm, 21*mm, 20*mm, 20*mm, 27*mm])

h2("5.2 Result on train, and why it is not the number to quote")

table([
    ["Box h (px)", "n", "median Z_true", "bias", "p25", "p75", "median |err|"],
    ["15-30", "975", "68.5 m", "0.0%", "-17%", "+29%", "21.3%"],
    ["30-60", "688", "38.4 m", "+0.1%", "-23%", "+17%", "22.5%"],
    ["60+", "331", "19.8 m", "-5.6%", "-24%", "+8%", "19.1%"],
], widths=[23*mm, 16*mm, 27*mm, 21*mm, 20*mm, 20*mm, 27*mm])

p("The train numbers are better, and they are better <b>by "
  "construction</b>. The prior is the median of that exact population, so "
  "near-zero bias in the middle bins is forced rather than earned. "
  "Reporting 21% would have been reporting a quantity fitted to its own "
  "evaluation set. Section 8 treats this as one of three validation errors "
  "found during development.")

h2("5.3 What the numbers say")

p("Median absolute error is flat at 23.5 to 24.7 percent while median "
  "distance changes by a factor of 3.5, from 18.4 m to 63.9 m.")

p("That flatness is the finding. If pixel quantisation dominated, the "
  "smallest and most distant signs would be dramatically worse, because "
  "dZ/Z = dh/h says a one-pixel error on a 15-pixel box is 6.7 percent "
  "while the same pixel on a 60-pixel box is 1.7 percent. The error does "
  "not scale that way, so pixel precision is not the limiting factor.")

p("What does scale that way is nothing, because the size-prior error is "
  "multiplicative and range-independent. The measured 23 to 25 percent sits "
  "directly on top of the -12% / +30% floor computed independently in "
  "Stage 1. Two separate measurements agreeing is the reason this "
  "conclusion is stated with confidence.")

h2("5.4 The bias sign flip")

p("Bias runs +9.0% at 64 m, +3.1% at 36 m, and -13.3% at 18 m. The trend "
  "is monotonic and crosses zero.")

p("The likely mechanism: close signs are disproportionately Groesse 1 at "
  "420 mm. Assuming 650 mm for a 420 mm sign overestimates its physical "
  "size, and an overestimated size with a correctly measured pixel height "
  "produces an underestimated range. The val size distribution supports "
  "this, since its excess mass sits precisely in the 400 to 500 mm bin, and "
  "the near-bin bias is more negative on val (-13.3%) than on train "
  "(-5.6%), tracking the larger Groesse 1 fraction.")

h2("5.5 The excluded regime")

p("Signs below 15 px box height are excluded from the error columns. At "
  "that size the predicted range exceeds 100 m, where stereo disparity "
  "falls below about 5 px. Disparity of 5 px on a thin structure is at the "
  "edge of SGM reliability, which means the reference carries more "
  "uncertainty than the estimate being tested. Measuring against it would "
  "be measuring noise.")

p("The threshold is stated on <b>box height in pixels</b>, an observable "
  "image quantity, not on true distance. This distinction is not "
  "cosmetic; Section 8 explains why a distance-based cutoff broke the "
  "evaluation.")

p("Validated envelope: roughly <b>18 to 64 m</b>.")

S.append(PageBreak())

# ============================================================ STAGE 3
h1("6. Stage 3: the detector")

h2("6.1 Split design, and the leak it prevents")

p("Three splits are required, not two, and the reason is subtle enough "
  "that the first attempt got it wrong.")

table([
    ["Purpose", "Cities", "Images", "Boxes"],
    ["Detector training", "15 train cities", "2,465", "17,869"],
    ["Checkpoint selection", "ulm, weimar, zurich", "333", "1,868"],
    ["Pipeline evaluation", "frankfurt, lindau, munster", "472", "3,900"],
], widths=[42*mm, 52*mm, 24*mm, 24*mm])

p("YOLO selects best.pt by performance on its validation split. If that "
  "split is the same data the pipeline is later scored on, the checkpoint "
  "has been chosen using the test set, and the end-to-end number inherits "
  "that selection. Cityscapes val is therefore reserved entirely, and the "
  "detector's own validation set is carved out of train.")

h2("6.2 Data preparation")

p("gtFine polygons are converted to axis-aligned YOLO-format boxes. Boxes "
  "below 8 px in either dimension are dropped: 1,037 from train, 94 from "
  "detector-val, 208 from the test set. Such boxes carry no learnable "
  "signal and contribute noise to the loss. The drop threshold at 8 px "
  "roughly aligns with the 15 px evaluation exclusion, so training and "
  "evaluation populations are not wildly mismatched.")

h2("6.3 Input resolution is the decisive parameter")

p("Cityscapes images are 2048 x 1024 and the median annotated sign is 22 px "
  "on its short side.")

table([
    ["imgsz", "Scale factor", "Median sign becomes", "Learnable?"],
    ["640", "0.3125", "6.9 px", "No"],
    ["1280", "0.625", "13.8 px", "Marginally"],
], widths=[22*mm, 32*mm, 48*mm, 32*mm], highlight=[2])

p("The P3 detection head has stride 8. At imgsz 640 the median sign is "
  "smaller than a single output cell, so it cannot be represented at all. "
  "Running the Ultralytics default on this dataset produces a poor mAP and "
  "invites the wrong diagnosis: the data looks hard, when in fact the input "
  "resolution destroyed the signal before the network saw it.")

p("imgsz 1280 was used. This is the single most consequential "
  "hyperparameter in the project and it is not a tuning matter.")

h2("6.4 Training")

p("Single-class YOLO11s, 9.43 M parameters, 21.7 GFLOPs. Trained on an "
  "8 GB RTX 4060 laptop GPU.")

p("Ultralytics autobatch probed batch 8, hit CUDA out of memory, and fell "
  "back to batch 1. Batch 1 was rejected: BatchNorm statistics from "
  "single-image batches are unreliable and the wall-clock cost is "
  "prohibitive. An explicit batch of 4 fit at 4.33 GB of 8 GB.")

code("yolo detect train model=yolo11s.pt data=data/yolo/data.yaml \\\n"
     "    imgsz=1280 epochs=100 batch=4 patience=20")

p("Training stopped at epoch 78 with patience 20, best checkpoint near "
  "epoch 58. Metrics on the held-out detector-validation cities:")

table([
    ["Metric", "Value"],
    ["Precision", "0.769"],
    ["Recall", "0.676"],
    ["mAP@50", "0.767"],
    ["mAP@50-95", "0.485"],
], widths=[45*mm, 30*mm])

p("Recall 0.676 is the number that matters for this project, not mAP. Every "
  "missed sign is a sign with no distance estimate, and misses are not "
  "distributed evenly.")

S.append(PageBreak())

# ============================================================ STAGE 4
h1("7. Stage 4: the end-to-end pipeline")

h2("7.1 Method")

p("Detector boxes replace annotation boxes in the ranging equation. Ground "
  "truth signs are matched to predictions at IoU >= 0.5, and the "
  "<i>predicted</i> box height drives Z_pred, so localisation error "
  "propagates as the geometry says it should.")

p("Two error columns are reported, and reporting both is the point:")

table([
    ["Column", "Population", "Why"],
    ["|err| detected", "Signs the detector found",
     "The accuracy of estimates that exist"],
    ["|err| all", "Every annotated sign, miss = infinite error",
     "The accuracy of the system, including what it never saw"],
], widths=[30*mm, 58*mm, 67*mm], align_right_from=9)

p("Reporting only the first would be selective reporting by omission. "
  "Misses concentrate in small boxes, which are the far-range signs where "
  "geometry is already weakest, so the surviving population is "
  "systematically easier than the full one.")

h2("7.2 Result at conf 0.25")

table([
    ["GT h (px)", "n", "recall", "med Z_true", "bias", "p25", "p75",
     "|err| det", "|err| all"],
    ["0-15", "337", "34.7%", "120.9 m", "+2.3%", "-21%", "+26%", "22.5%",
     "undefined"],
    ["15-30", "730", "73.8%", "63.9 m", "+3.1%", "-12%", "+37%", "22.2%",
     "35.2%"],
    ["30-60", "527", "91.3%", "36.0 m", "+1.8%", "-19%", "+40%", "25.0%",
     "29.7%"],
    ["60+", "223", "94.2%", "18.4 m", "-11.7%", "-28%", "+8%", "22.5%",
     "23.8%"],
], widths=[19*mm, 13*mm, 17*mm, 22*mm, 18*mm, 16*mm, 16*mm, 18*mm, 21*mm])

figure("error_vs_range.png",
       "Signed ranging error against reference distance, ground-truth boxes "
       "versus detector boxes. Shaded band is the interquartile range. "
       "Signed rather than absolute error is plotted because the direction "
       "of the bias is the finding.")

h2("7.3 The central result: localisation is not the bottleneck")

p("Ground-truth boxes give 23.5 to 24.7 percent median absolute error on "
  "these images. Detector boxes give 22.2 to 25.0 percent. Bias tracks "
  "closely as well: +3.1 / +1.8 / -11.7 against +9.0 / +3.1 / -13.3.")

p("<b>The difference is inside the noise, and the geometry predicted "
  "otherwise.</b>")

p("dZ/Z = dh/h says a two-pixel error on a thirty-pixel box is a seven "
  "percent distance error, so detector boxes should visibly degrade the "
  "estimate. They do not, because YOLO localises to a pixel or two while "
  "the fixed 650 mm prior is wrong by plus or minus 25 percent. The "
  "dominant error term swamps the added one entirely.")

p("This is a falsified prediction with a clean explanation, and it is the "
  "most useful thing the project established. It says that effort spent on "
  "better box regression is wasted until the size prior is fixed.")

h2("7.4 What detection actually costs: coverage")

figure("coverage_vs_range.png",
       "Fraction of annotated signs that receive a distance estimate, by "
       "reference distance. Detection does not degrade estimates; it "
       "removes them, and it removes them exactly where they are hardest to "
       "produce.")

p("Coverage is 74.1 percent overall. Broken down by range it falls from "
  "94.2 percent at 18 m to 34.7 percent beyond 100 m. In the 15 to 30 px "
  "band, which dominates the validation range at around 64 m, one sign in "
  "four produces nothing at all.")

p("The all-GT column makes this visible: 35.2 percent error at 15-30 px "
  "against 22.2 percent for the detected subset. The gap is the cost of "
  "the misses.")

h2("7.5 Selecting the operating point")

p("The confidence threshold was measured rather than inherited.")

table([
    ["conf", "Coverage", "Predictions", "False positives", "FP/image",
     "Precision"],
    ["0.40", "64.9%", "2,703", "470", "0.99", "0.826"],
    ["0.25", "74.1%", "3,864", "1,045", "2.21", "0.730"],
    ["0.10", "81.1%", "6,221", "2,739", "5.79", "0.560"],
], widths=[18*mm, 25*mm, 27*mm, 32*mm, 24*mm, 25*mm], highlight=[2])

figure("operating_point.png",
       "Coverage against precision at three confidence thresholds. The knee "
       "is at 0.25.", width=125*mm)

p("The informative quantity is the marginal exchange rate, which neither "
  "column shows directly:")

table([
    ["Step", "Signs gained", "False positives added", "FP per sign"],
    ["0.40 -> 0.25", "+167", "+575", "3.4"],
    ["0.25 -> 0.10", "+126", "+1,694", "13.4"],
], widths=[32*mm, 30*mm, 45*mm, 30*mm])

p("The cost per recovered sign quadruples below 0.25. That is a knee, and "
  "it happens to fall on the Ultralytics default value. The threshold is "
  "the same as the default; the difference is that it is now a measured "
  "choice.")

h2("7.6 False positives cannot be range-gated away")

p("An obvious mitigation would be discarding phantom detections by "
  "implausible range. It does not work here. False-positive box heights "
  "track the real sign distribution almost exactly, p50 of 25 px and p90 of "
  "66 px against a 22 px real median, implying phantom signs at "
  "approximately 59 m. That is squarely inside the validated envelope.")

h2("7.7 Precision is a bound, not a point")

p("False positives were counted against <b>all</b> traffic-sign polygons, "
  "not the near-square ranging subset, so correctly detecting a rectangular "
  "direction sign is not penalised. Getting this wrong would have inflated "
  "the false-positive count severely.")

p("Relaxing the match threshold at conf 0.25:")

table([
    ["Match IoU", "False positives", "Precision"],
    ["0.5", "1,045", "0.730"],
    ["0.4", "878", "0.773"],
    ["0.3", "764", "0.802"],
    ["0.2", "699", "0.819"],
    ["0.1", "662", "0.829"],
], widths=[30*mm, 40*mm, 30*mm])

p("Thirty-seven percent of strict false positives do overlap a real sign, "
  "and the curve flattens by IoU 0.3, so the recoverable ones are all "
  "accounted for by then. The likely cause is multi-plate assemblies "
  "annotated as a single polygon: detecting each plate correctly still "
  "scores below threshold against the merged bounding box.")

p("The remaining 662 predictions, 17 percent of all detections, touch no "
  "annotated sign at any threshold. These have not been inspected, so it is "
  "not known whether they are hallucinations, sign backs, or objects "
  "Cityscapes simply did not label. Precision is therefore reported as a "
  "range, <b>0.73 to 0.83</b>, rather than a false point estimate.")

S.append(PageBreak())

# ============================================================ ERRORS
h1("8. Three validation errors found during development")

p("All three would have produced numbers that looked entirely reasonable. "
  "None was caught by a crash, a warning, or an implausible value. They are "
  "documented because the process that found them is more transferable than "
  "the result.")

h2("8.1 Filters that selected on one side of the comparison")

p("Two filters were tried and rejected.")

table([
    ["Filter", "Bias in smallest bin", "Effect"],
    ["Z_true < 120 m", "+44.6%", "removed far truth, kept far predictions"],
    ["disparity >= 6 px", "+102.6%", "same failure, opposite direction"],
], widths=[35*mm, 40*mm, 80*mm], align_right_from=9)

p("Both select using the reference side only. For a fixed observed box "
  "height, dropping samples with large true distance leaves behind a group "
  "the monocular model appears to systematically overestimate, because the "
  "predictions were never filtered. The bias is an artefact of the "
  "filtering rule, not a property of the ranging model.")

p("<b>Rule adopted:</b> a filter must be independent of both Z_true and "
  "Z_pred, or applied symmetrically to both. The final analysis filters on "
  "box height in pixels, which is observable without knowing either.")

p("Notably, the second filter was introduced as a <i>fix</i> for the "
  "first, and made the problem worse. The symptom in both cases was a "
  "one-sided bias appearing in exactly one bin, which is the signature to "
  "watch for.")

h2("8.2 A prior evaluated on the data it was fitted to")

p("The first error curve was computed on the same five train cities the "
  "650 mm prior was derived from. Because the prior is the median of that "
  "population, near-zero bias in the middle bins is forced rather than "
  "measured.")

p("Moving to the held-out val split raised median absolute error from 21 "
  "percent to 24 percent and revealed bias of up to -13 percent. The 21 "
  "percent figure was never a real measurement.")

p("The prior was re-derived on val purely as a diagnostic, giving 641 mm "
  "against 651 mm, confirming transfer. It was <b>not</b> re-fitted.")

h2("8.3 A detector checkpoint selected on the evaluation set")

p("The first data preparation script built two YOLO splits and pointed the "
  "validation split at Cityscapes val, which is the pipeline test set. "
  "best.pt was therefore chosen by performance on the exact images the "
  "end-to-end result would be measured on.")

p("Compounding this, the preparation script wrote into existing "
  "directories without clearing them, so a second run merged the old and "
  "new splits: 805 images where 333 were expected.")

p("Rebuilt as a three-way split with an idempotent rebuild. The corrected "
  "run scored mAP@50 of 0.767 against the leaked run's 0.750, so the leak "
  "had <b>no measurable effect</b>. It is recorded because the result was "
  "not defensible as produced, not because the numbers changed.")

h2("8.4 A note on duplicate annotations")

p("Ultralytics reported duplicate labels during training, in one case 8 "
  "identical boxes on a single image. Cityscapes annotates some signs with "
  "overlapping polygons whose axis-aligned bounding boxes collapse to "
  "identical coordinates. Stage 4 deduplicates by box coordinates; the "
  "resulting sign count of 1,817 matches Stage 2 exactly, so duplicates "
  "were not inflating the earlier measurement.")

S.append(PageBreak())

# ============================================================ CODE
h1("9. Code walkthrough")

p("Seven scripts, run in order. All read from <font face='Courier'>data/"
  "</font> and none modify it. Stages 0 to 2 take the split as first "
  "argument and an optional city count as second, so that published train "
  "numbers remain reproducible after the split became parameterised.")

h2("9.1 tools/stage0_check.py")

h3("Purpose: establish whether the reference measurement exists at all")

p("<b>Reads:</b> gtFine polygons, camera.json, disparity PNGs.<br/>"
  "<b>Writes:</b> nothing. Prints coverage, size, and distance "
  "distributions.")

p("For each annotated <font face='Courier'>traffic sign</font> polygon it "
  "takes the axis-aligned bounding box, clips it to image bounds, extracts "
  "the disparity patch, and computes reference distance from the median of "
  "valid disparity pixels. A sign counts as usable if at least 20 percent "
  "of its patch carries valid disparity and the resulting distance falls in "
  "a plausible band.")

p("Key details:")
bullets([
    "Polygon coordinates are floats and must be floored/ceiled to int "
    "before slicing, and clipped to image bounds. Some Cityscapes polygons "
    "run past the frame edge; without clipping the patch silently truncates.",
    "<font face='Courier'>patch.size == 0</font> must be guarded "
    "separately from the polygon extent check. A polygon can pass a "
    "width/height test and still produce an empty slice.",
    "The 20 percent valid-fill requirement rejects boxes where disparity "
    "is mostly missing rather than trusting a median over three pixels.",
])

h2("9.2 tools/stage0_bleed_check.py")

h3("Purpose: test whether median disparity is contaminated by background")

p("<b>Reads:</b> same three sources.<br/>"
  "<b>Writes:</b> nothing. Prints the median-versus-p90 gap by box size.")

p("Computes two distances per sign, one from median disparity and one from "
  "the 90th percentile, and reports their relative gap stratified by box "
  "size. Stratification is essential: a single aggregate gap would hide the "
  "size dependence, and the size dependence is what distinguishes background "
  "bleed from plate tilt.")

h2("9.3 tools/stage1_size_prior.py")

h3("Purpose: derive the physical size prior from data rather than assumption")

p("<b>Reads:</b> same three sources.<br/>"
  "<b>Writes:</b> <font face='Courier'>results/implied_height_&lt;split&gt;"
  ".csv</font>, plus a printed histogram.")

p("Inverts the ranging equation per sign to recover implied physical "
  "height, then restricts to a clean subset (h >= 30 px, near-square) "
  "before reading the distribution. Uses f_y, not f_x, because a vertical "
  "extent is being inverted.")

p("The printed ASCII histogram in 100 mm bins was deliberate: the shape of "
  "the distribution, not just its median, is what identifies the size "
  "classes.")

h2("9.4 tools/stage2_error_curve.py")

h3("Purpose: measure geometric ranging error with perfect boxes")

p("<b>Reads:</b> same three sources.<br/>"
  "<b>Writes:</b> nothing. Prints the stratified error table.")

p("Applies Z_pred = f_y * 0.650 / h_px to ground-truth boxes and compares "
  "against stereo depth, stratified into four box-height bins.")

p("Two design decisions carry weight:")
bullets([
    "<b>Signed error, not absolute.</b> Absolute error hides direction. A "
    "uniform +8% bias would indicate a correctable prior offset; near-zero "
    "bias with wide spread indicates irreducible size ambiguity. These "
    "demand different responses and |error| cannot distinguish them.",
    "<b>The near-square filter runs in the main loop</b>, so the prior is "
    "applied only to the population it was derived from. Applying a 650 mm "
    "height prior to a rectangular direction sign is guaranteed nonsense.",
])

h2("9.5 tools/stage3_prep.py")

h3("Purpose: build leak-free YOLO splits")

p("<b>Reads:</b> gtFine polygons, leftImg8bit images.<br/>"
  "<b>Writes:</b> <font face='Courier'>data/yolo/{images,labels}/"
  "{train,val,test}/</font> and <font face='Courier'>data.yaml</font>.")

p("Converts polygons to normalised YOLO boxes and copies matching images. "
  "Three behaviours are load-bearing:")

bullets([
    "<b>The three-way split.</b> Cityscapes val goes to <font "
    "face='Courier'>test/</font>, and data.yaml deliberately omits it, so "
    "no training run can select a checkpoint on it.",
    "<b>Idempotent rebuild.</b> Output directories are removed before "
    "writing. Without this, rerunning after a split change merges old and "
    "new files silently.",
    "<b>MIN_PX = 8 drop.</b> Boxes below 8 px in either dimension are "
    "unlearnable and add loss noise. The drop count is printed rather than "
    "hidden.",
])

h2("9.6 tools/stage4_pipeline_eval.py")

h3("Purpose: measure the full pipeline, honestly")

p("<b>Reads:</b> trained weights, leftImg8bit, gtFine, camera, "
  "disparity.<br/>"
  "<b>Writes:</b> <font face='Courier'>results/pipeline_val_conf&lt;c&gt;"
  ".csv</font> with columns h_px, Z_true, Z_pred_det, Z_pred_gt.")

p("Runs inference at imgsz 1280, matches each ground-truth sign to its "
  "best-overlapping prediction, and drives the ranging equation from the "
  "predicted box height. Takes weights path and confidence threshold as "
  "arguments so the operating-point sweep is one command per threshold.")

p("Four decisions that determine whether the output means anything:")
bullets([
    "<b>Predicted box height drives Z_pred</b>, not ground truth. "
    "Otherwise localisation error would not propagate and the whole "
    "exercise would be circular.",
    "<b>Misses are recorded as NaN and scored as infinite error</b> in the "
    "all-GT column, rather than dropped. Dropping them would report the "
    "accuracy of the easy subset.",
    "<b>False positives are matched against all sign polygons</b>, not the "
    "near-square ranging subset. Matching against the filtered set would "
    "count every correct detection of a rectangular sign as a false "
    "positive.",
    "<b>Best-IoU per prediction is recorded once</b> and thresholded "
    "afterwards, so the full precision-versus-match-threshold curve comes "
    "from a single inference pass. Changing the match threshold directly "
    "would also change recall and confound the two.",
])

p("The population filter is applied to the <i>ground-truth</i> box so the "
  "numbers stay comparable with Stage 2. A deployed system would filter on "
  "predicted aspect ratio instead, which is a different and slightly worse "
  "number.")

h2("9.7 tools/figures.py")

h3("Purpose: turn saved CSVs into the four result figures")

p("<b>Reads:</b> <font face='Courier'>results/*.csv</font>.<br/>"
  "<b>Writes:</b> <font face='Courier'>figures/*.png</font>.")

p("Reads from disk rather than re-running inference, so plotting iterations "
  "cost seconds instead of minutes. Bins by reference distance on a "
  "geometric scale, since range and box size are coupled and both span more "
  "than a decade.")

p("Plots signed error with an IQR band rather than absolute error, for the "
  "reason given in 9.4. The operating-point figure's three points are "
  "hardcoded from the threshold sweep, since nothing writes them to disk.")

S.append(PageBreak())

# ============================================================ SUMMARY
h1("10. Summary of results")

table([
    ["Quantity", "Value", "Measured on"],
    ["Reference coverage", "88% of annotated signs", "train, 5 cities"],
    ["Disparity contamination", "2-4%, shrinks with box size",
     "train, 5 cities"],
    ["Implied sign height", "651 mm median, IQR 574-842",
     "train, 991 signs"],
    ["Prior transfer", "641 mm on val vs 651 on train", "val, 727 signs"],
    ["Size-ambiguity floor", "-12% / +30%", "derived"],
    ["Geometry only, GT boxes", "23.5-24.7% median |error|", "val, held out"],
    ["Detector mAP@50", "0.767", "ulm/weimar/zurich"],
    ["Detector recall", "0.676", "ulm/weimar/zurich"],
    ["End-to-end |error|", "22.2-25.0% on detected signs", "val, held out"],
    ["End-to-end coverage", "74.1%", "val, held out"],
    ["Precision", "0.73 to 0.83", "val, held out"],
    ["Validated envelope", "18-64 m", "val, held out"],
], widths=[45*mm, 62*mm, 45*mm], align_right_from=9)

h2("The three-number statement")

p("<b>A plus-or-minus 24 percent ranging instrument over 18 to 64 metres, "
  "with 74 percent coverage and precision between 0.73 and 0.83.</b>")

p("Detection contributes almost nothing to the error of estimates it "
  "produces. Its entire cost is coverage, which falls from 94 percent at "
  "18 m to 35 percent beyond 100 m. A single accuracy figure would hide "
  "the part that matters most.")

h1("11. Limitations")

h2("11.1 The size prior is the ceiling")

p("Everything is capped at roughly plus or minus 24 percent by not knowing "
  "which size class a sign belongs to. This is not a tuning problem. "
  "Better box regression, a larger detector, higher input resolution, and "
  "better calibration all leave it untouched.")

p("Fixing it requires per-class priors, which requires sign type, which "
  "Cityscapes does not provide. GTSDB provides type but no depth. Neither "
  "dataset alone supports the fix.")

h2("11.2 Known unquantified gaps")

bullets([
    "662 false positives, 17 percent of all detections, overlap no "
    "annotated sign at any IoU threshold and have not been visually "
    "inspected.",
    "The population filter uses ground-truth aspect ratio. A deployed "
    "system must filter on predicted aspect, which will be slightly worse "
    "and is unmeasured.",
    "No temporal component. Every frame is treated independently, so "
    "frame-to-frame jitter in the range estimate is unknown.",
    "Single camera, single dataset. Transfer to a different camera is "
    "untested.",
    "Signs beyond roughly 100 m have no validated error figure, because "
    "the stereo reference itself becomes unreliable there.",
])

h2("11.3 Dataset licence")

p("Cityscapes is used under its non-commercial licence. No image, "
  "disparity map, polygon file, or derived crop is redistributed in the "
  "repository. Download instructions are provided instead.")

h1("12. What would come next")

table([
    ["Priority", "Work", "Value", "Cost"],
    ["1", "Sign-type classification, per-class priors",
     "Only thing that moves the 24%", "Large, uncertain"],
    ["2", "GTSDB-trained detector on same val images",
     "Measures camera domain gap as a subtraction", "One weekend"],
    ["3", "INT8 quantisation, latency on target hardware",
     "Deployment realism", "One weekend"],
    ["4", "Temporal stability across sequence frames",
     "Real ADAS failure mode, rarely measured", "Medium"],
    ["5", "Inspect the 662 unexplained false positives",
     "Closes the one open question", "Ten minutes"],
], widths=[16*mm, 50*mm, 55*mm, 32*mm], align_right_from=9)

p("Item 1 is the only one that changes the headline number. Items 2 to 5 "
  "improve what is known about the system as it stands.")

h1("13. Reproduction")

p("Download <font face='Courier'>gtFine_trainvaltest</font>, <font "
  "face='Courier'>camera_trainvaltest</font>, <font face='Courier'>"
  "disparity_trainvaltest</font>, and <font face='Courier'>"
  "leftImg8bit_trainvaltest</font> from cityscapes-dataset.com into <font "
  "face='Courier'>data/</font>.")

code("# feasibility and prior derivation, five train cities\n"
     "python tools/stage0_check.py train 5\n"
     "python tools/stage0_bleed_check.py train 5\n"
     "python tools/stage1_size_prior.py train 5\n"
     "\n"
     "# geometry-only error, held-out val split\n"
     "python tools/stage2_error_curve.py val\n"
     "\n"
     "# detector data prep and training\n"
     "python tools/stage3_prep.py\n"
     "yolo detect train model=yolo11s.pt data=data/yolo/data.yaml \\\n"
     "    imgsz=1280 epochs=100 batch=4 patience=20\n"
     "\n"
     "# end-to-end evaluation, second argument is confidence threshold\n"
     "python tools/stage4_pipeline_eval.py path/to/best.pt 0.25\n"
     "\n"
     "# figures\n"
     "python tools/figures.py")

p("Hardware used: RTX 4060 Laptop, 8 GB VRAM. Training ran approximately "
  "2.5 minutes per epoch at imgsz 1280 with batch 4, stopping at epoch 78.")

# ============================================================ BUILD
doc = SimpleDocTemplate(
    OUT, pagesize=A4,
    leftMargin=20*mm, rightMargin=20*mm,
    topMargin=18*mm, bottomMargin=20*mm,
    title="Monocular Sign Ranging - Project Report",
    author="Vishal Selvaraju",
)
doc.build(S, onFirstPage=footer, onLaterPages=footer)
print(f"wrote {OUT}")
