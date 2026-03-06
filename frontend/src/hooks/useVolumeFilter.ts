import { useState } from 'react';

export const useVolumeFilter = (initialThreshold: number = 1000) => {
    const [volumeThreshold, setVolumeThreshold] = useState<number>(initialThreshold);

    return { volumeThreshold, setVolumeThreshold };
};
