#!/usr/bin/env python

import logging
import subprocess
import sys
import tempfile

import PyPDF2


PDFTOTEXT_BINARY = "/usr/bin/pdftotext"
TESSERACT_BINARY = "/usr/bin/tesseract"
TESSERACT_OPTIONS = ["-l", "eng"]
GHOSTSCRIPT_BINARY = "/usr/bin/gs"


logging.basicConfig(filename="ocr_pdftotext.log", level=logging.DEBUG)
logger = logging.getLogger("ocr_pdftotext")
logger.setLevel(logging.DEBUG)


def log_arguments(module, args):
    logging.getLogger(module).debug("Called with args: " + " ".join(args))


def seems_humanreadable(txt):
    return False


def run_and_capture(module, args):
    completed_proc = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if completed_proc.returncode != 0:
        logging.getLogger(module).error(completed_proc.stderr)
    return completed_proc


def rasterize_pdf_page(input_file, output_file, page):
    ghostscript_args = [GHOSTSCRIPT_BINARY,
                        '-dQUIET',
                        '-dSAFER',
                        '-dBATCH',
                        '-dNOPAUSE',
                        '-sDEVICE=png16m',
                        '-dFirstPage=%d' % page,
                        '-dLastPage=%d' % page,
                        '-o', output_file,
                        '-r300x300',
                        input_file]
    log_arguments("ghostscript", ghostscript_args)
    subprocess.run(ghostscript_args)


def tesseract_pdf_page(input_file, page):
    with tempfile.NamedTemporaryFile() as output_file:
        rasterize_pdf_page(input_file, output_file.name, page)
        tesseract_args = [TESSERACT_BINARY, output_file.name, "stdout"] + TESSERACT_OPTIONS
        log_arguments("tesseract", tesseract_args)
        tesseract = run_and_capture("tesseract", tesseract_args)
        return tesseract.stdout


def tesseract_pdf(input_file):
    pdf_reader = PyPDF2.PdfFileReader(input_file)
    num_pages = pdf_reader.getNumPages()
    tesseract_results = [tesseract_pdf_page(input_file, i + 1) for i in range(num_pages)]
    return b'\n'.join(tesseract_results)


def main(args):
    log_arguments("ocr_pdftotext", args)
    pdftotext_args = [PDFTOTEXT_BINARY] + args[:-1] + ["-"]
    log_arguments("pdftotext", pdftotext_args)
    pdftotext = run_and_capture("pdftotext", pdftotext_args)
    if seems_humanreadable(pdftotext.stdout.decode("UTF-8")):
        with open(args[-1], "wb") as outf:
            outf.write(pdftotext.stdout)
    else:
        tesseract_result = tesseract_pdf(args[-2])
        with open(args[-1], "wb") as outf:
            outf.write(tesseract_result)


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except Exception as e:
        logging.getLogger("ocr_pdftotext").error(e)
