export const TEXT_FILE_ACCEPT = '.json,.geojson,.txt,.md,.csv,.tsv';
export const TEXT_FILE_HELP = '';

export function validateFiles(files: File[]): void {
    if (files.length > 3 || files.some(file => file.size > 10 * 1024 * 1024)) {
        throw new Error('Attach up to three files, maximum 10 MB each.');
    }
    if (files.some(file => !TEXT_FILE_ACCEPT.split(',').some(extension => file.name.toLowerCase().endsWith(extension)))) {
        throw new Error(TEXT_FILE_HELP);
    }
}
