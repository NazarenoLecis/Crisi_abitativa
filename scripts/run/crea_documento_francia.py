from pathlib import Path

from PIL import Image
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.utils import ImageReader


root = Path(__file__).resolve().parents[2]
outputDir = root / "outputs" / "francia" / "documento"
outputPdf = outputDir / "crisi_abitativa_situazione_francese.pdf"

figures = [
    (
        "Prezzi delle case, affitti, redditi e inflazione",
        root / "outputs/reel_parigi_9mq/grafici/02_prezzi_affitti_redditi_inflazione.png",
    ),
    (
        "Rapporto prezzi/reddito nel confronto internazionale",
        root / "outputs/reel_parigi_9mq/grafici/03_rapporto_prezzi_reddito_ocse.png",
    ),
    (
        "Rapporto prezzi/affitti nel confronto internazionale",
        root / "outputs/reel_parigi_9mq/grafici/04_rapporto_prezzi_affitti_ocse.png",
    ),
    (
        "Permessi di costruzione abitazioni",
        root / "outputs/reel_parigi_9mq/grafici/05_permessi_costruzione_abitazioni.png",
    ),
    (
        "Investimenti in abitazioni in percentuale del PIL",
        root / "outputs/reel_parigi_9mq/grafici/06_investimenti_abitazioni_pil.png",
    ),
    (
        "Abitazioni non occupate nello stock abitativo",
        root / "outputs/reel_parigi_9mq/grafici/07_case_non_occupate_eurostat.png",
    ),
    (
        "Abitazioni vuote o stagionali",
        root / "outputs/reel_parigi_9mq/grafici/08_abitazioni_vuote_stagionali_ocse.png",
    ),
    (
        "Sovraccarico dei costi abitativi per gli inquilini",
        root / "outputs/reel_parigi_9mq/grafici/10_sovraccarico_costi_inquilini.png",
    ),
    (
        "Titolo di godimento dell'abitazione",
        root / "outputs/francia/charts/confronti/francia_ue_titolo_godimento_abitazione.png",
    ),
    (
        "Proprietari di casa per quintile di reddito",
        root / "outputs/francia/charts/confronti/francia_ue_proprietari_casa_reddito.png",
    ),
    (
        "Accesso a un'abitazione adeguata e rischio di povert\u00e0",
        root / "outputs/francia/charts/confronti/francia_ue_accesso_abitazione_adeguata_poverta.png",
    ),
    (
        "Rischio di povert\u00e0 prima e dopo i costi abitativi",
        root / "outputs/francia/charts/confronti/francia_ue_rischio_poverta_costi_abitativi.png",
    ),
    (
        "Et\u00e0 media di uscita dalla casa dei genitori",
        root / "outputs/francia/charts/confronti/francia_ue_eta_uscita_casa_genitori.png",
    ),
    (
        "Abitazioni per 1.000 abitanti",
        root / "outputs/francia/charts/confronti/oecd_ahd_abitazioni_per_1000_abitanti.png",
    ),
    (
        "Prezzi immobiliari nei dipartimenti francesi",
        root / "outputs/francia/charts/focus/francia_range_prezzi_dvf_dipartimenti.png",
    ),
    (
        "Prezzi di vendita nei comuni francesi",
        root / "outputs/francia/charts/mappe/francia_comuni_prezzi_vendita_mq.png",
    ),
    (
        "Affitti nei comuni francesi",
        root / "outputs/francia/charts/mappe/francia_comuni_affitti_mq_mese.png",
    ),
    (
        "Affitto di 40 mq rispetto al reddito nei comuni francesi",
        root / "outputs/francia/charts/mappe/francia_comuni_affitto_40mq_reddito.png",
    ),
    (
        "Anni di reddito per acquistare 80 mq nei comuni francesi",
        root / "outputs/francia/charts/mappe/francia_comuni_anni_reddito_per_80mq.png",
    ),
    (
        "Parigi e Milano: affitti, prezzi e redditi",
        root / "outputs/francia/charts/focus/parigi_milano_confronto_affitti_vendita_reddito.png",
    ),
    (
        "Parigi: affitti, vendita e reddito",
        root / "outputs/francia/charts/focus/parigi_focus_affitti_vendita_reddito.png",
    ),
    (
        "Parigi: prezzi di vendita al metro quadro",
        root / "outputs/francia/charts/mappe/parigi_prezzi_vendita_mq.png",
    ),
    (
        "Parigi: affitti al metro quadro al mese",
        root / "outputs/francia/charts/mappe/parigi_affitti_mq_mese.png",
    ),
    (
        "Parigi: affitto di 40 mq rispetto al reddito",
        root / "outputs/francia/charts/mappe/parigi_affitto_40mq_reddito.png",
    ),
    (
        "Parigi: anni di reddito per acquistare 80 mq",
        root / "outputs/francia/charts/mappe/parigi_anni_reddito_per_80mq.png",
    ),
]


def textLines(pdf, text, x, y, size=10.5, leading=14, width=6.7 * inch):
    style = ParagraphStyle(
        "Body",
        fontName="Helvetica",
        fontSize=size,
        leading=leading,
        textColor=colors.HexColor("#222222"),
        alignment=TA_LEFT,
    )
    paragraph = Paragraph(text, style)
    usedWidth, usedHeight = paragraph.wrap(width, 9 * inch)
    paragraph.drawOn(pdf, x, y - usedHeight)
    return y - usedHeight


def drawFooter(pdf, pageNumber):
    width, height = letter
    pdf.setStrokeColor(colors.HexColor("#d6d6d6"))
    pdf.line(0.65 * inch, 0.52 * inch, width - 0.65 * inch, 0.52 * inch)
    pdf.setFont("Helvetica", 8)
    pdf.setFillColor(colors.HexColor("#606060"))
    pdf.drawString(0.65 * inch, 0.34 * inch, "Elaborazioni di Nazareno Lecis")
    pdf.drawRightString(width - 0.65 * inch, 0.34 * inch, str(pageNumber))


def addCover(pdf):
    width, height = letter
    pdf.setFillColor(colors.HexColor("#111111"))
    pdf.setFont("Helvetica-Bold", 28)
    pdf.drawString(0.72 * inch, height - 1.15 * inch, "crisi abitativa: la situazione francese")
    pdf.setFont("Helvetica", 15)
    pdf.setFillColor(colors.HexColor("#444444"))
    pdf.drawString(0.72 * inch, height - 1.55 * inch, "Elaborazioni di Nazareno Lecis")
    pdf.setStrokeColor(colors.HexColor("#2f5f9d"))
    pdf.setLineWidth(2)
    pdf.line(0.72 * inch, height - 1.85 * inch, width - 0.72 * inch, height - 1.85 * inch)

    intro = (
        "Questo documento raccoglie una selezione di grafici sulla crisi abitativa in Francia. "
        "La prima parte colloca il caso francese nel confronto con l'Unione europea e con "
        "l'Italia: prezzi, affitti, redditi, permessi, investimenti, stock abitativo e indicatori "
        "sociali. La seconda parte restringe progressivamente il fuoco sul territorio francese, "
        "fino al caso di Parigi."
    )
    y = textLines(pdf, intro, 0.72 * inch, height - 2.45 * inch, size=11.5, leading=16)
    y -= 0.22 * inch
    note = (
        "Le fonti sono riportate nei footer dei singoli grafici. Dove possibile, le tavole "
        "mantengono la comparabilit\u00e0 con il formato del fact sheet europeo di riferimento; "
        "le mappe e i focus locali aggiungono una lettura territoriale."
    )
    textLines(pdf, note, 0.72 * inch, y, size=10.5, leading=15)

    pdf.setFont("Helvetica-Bold", 11)
    pdf.setFillColor(colors.HexColor("#111111"))
    pdf.drawString(0.72 * inch, 2.0 * inch, "Sequenza del documento")
    pdf.setFont("Helvetica", 10)
    pdf.setFillColor(colors.HexColor("#333333"))
    lines = [
        "1. Confronti Francia, UE27 e Italia",
        "2. Indicatori sociali e accessibilit\u00e0 economica",
        "3. Stock abitativo e geografia dei prezzi in Francia",
        "4. Focus Parigi",
    ]
    lineY = 1.72 * inch
    for line in lines:
        pdf.drawString(0.72 * inch, lineY, line)
        lineY -= 0.22 * inch


def fitImage(path, maxWidth, maxHeight):
    with Image.open(path) as image:
        imageWidth, imageHeight = image.size
    ratio = min(maxWidth / imageWidth, maxHeight / imageHeight)
    return imageWidth * ratio, imageHeight * ratio


def addFigurePage(pdf, number, title, path):
    width, height = letter
    pdf.setFillColor(colors.HexColor("#111111"))
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(0.65 * inch, height - 0.78 * inch, f"Figura {number}: {title}")

    maxWidth = width - 1.3 * inch
    maxHeight = height - 1.72 * inch
    imageWidth, imageHeight = fitImage(path, maxWidth, maxHeight)
    x = (width - imageWidth) / 2
    y = height - 1.08 * inch - imageHeight
    pdf.drawImage(ImageReader(str(path)), x, y, width=imageWidth, height=imageHeight, preserveAspectRatio=True)


def main():
    outputDir.mkdir(parents=True, exist_ok=True)
    missing = [str(path) for title, path in figures if not path.exists()]
    if missing:
        raise FileNotFoundError("\\n".join(missing))

    pdf = canvas.Canvas(str(outputPdf), pagesize=letter)
    pdf.setTitle("crisi abitativa: la situazione francese")
    pdf.setAuthor("Nazareno Lecis")
    addCover(pdf)
    drawFooter(pdf, 1)
    pdf.showPage()

    pageNumber = 2
    for number, item in enumerate(figures, start=1):
        title, path = item
        addFigurePage(pdf, number, title, path)
        drawFooter(pdf, pageNumber)
        pdf.showPage()
        pageNumber += 1

    pdf.save()
    print(outputPdf)


if __name__ == "__main__":
    main()
