// Match the API's content-sniffed JPEG/PNG contract. This is early feedback;
// the server remains responsible for validating the actual file bytes.
export const PHOTO_ACCEPT = 'image/jpeg,image/png'
export function photoSelectionError(files: readonly File[]): string {
  if (files.length < 1 || files.length > 4) return 'Choose 1–4 photos. Remove extra photos before building.'
  if (files.some(file => file.size > 8 * 1024 * 1024)) return 'Each photo must be 8 MB or smaller.'
  if (files.some(file => file.type ? !['image/jpeg', 'image/png'].includes(file.type) : !/\.(jpe?g|png)$/i.test(file.name))) {
    return 'Choose JPEG or PNG photos. Convert WebP or HEIC photos before uploading.'
  }
  return ''
}
