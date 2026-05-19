export function delegateDownloadBlob({
  blob,
  filename,
  createObjectURL,
  revokeObjectURL,
  createAnchor,
  appendToBody,
}) {
  const url = createObjectURL(blob)
  const anchor = createAnchor()
  anchor.href = url
  anchor.download = filename
  appendToBody(anchor)
  anchor.click()
  if (typeof anchor.remove === 'function') anchor.remove()
  revokeObjectURL(url)
}
