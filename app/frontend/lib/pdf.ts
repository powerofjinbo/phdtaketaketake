// In-browser document → text. PDFs go through pdf.js; plain-text files are
// read directly. Nothing is uploaded anywhere.

export async function pdfToText(file: File, maxPages = 12): Promise<string> {
  const pdfjs = await import("pdfjs-dist");
  pdfjs.GlobalWorkerOptions.workerSrc = new URL(
    "pdfjs-dist/build/pdf.worker.min.mjs",
    import.meta.url
  ).toString();
  const doc = await pdfjs.getDocument({ data: await file.arrayBuffer() }).promise;
  const pages = Math.min(doc.numPages, maxPages);
  let text = "";
  for (let i = 1; i <= pages; i++) {
    const page = await doc.getPage(i);
    const content = await page.getTextContent();
    text +=
      content.items
        .map((it) => ("str" in it ? (it as { str: string }).str : ""))
        .join(" ") + "\n";
  }
  return text;
}

export async function fileToText(file: File): Promise<string> {
  const isPdf =
    file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
  const text = isPdf ? await pdfToText(file) : await file.text();
  if (!text.trim()) {
    throw new Error(
      `Could not extract any text from ${file.name} (is it a scanned image?). Try a text-based PDF or a .txt copy.`
    );
  }
  return text;
}
