export function formatFootprintVolume(volume: number | undefined | null): string {
    if (volume === 0 || !volume) return "0";

    // If it's a whole number, return as is
    if (Number.isInteger(volume)) {
        return volume.toString();
    }

    // For fractional numbers, format to a maximum of 5 decimal places,
    // and remove trailing zeroes by parsing as float.
    return parseFloat(volume.toFixed(5)).toString();
}
