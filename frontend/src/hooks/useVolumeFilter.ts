import { useState } from 'react';

export const useVolumeFilter = (initialThreshold: number = 1000) => {
    const [volumeThreshold, setVolumeThreshold] = useState<number>(initialThreshold);
    const [volumeMode, setVolumeMode] = useState<'base' | 'quote'>('base');

    return { volumeThreshold, setVolumeThreshold, volumeMode, setVolumeMode };
};
