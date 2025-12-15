// Region type import removed as it was unused


export function bboxToRect(bbox: [number, number, number, number]) {
    const [x1, y1, x2, y2] = bbox;
    return {
        x: x1,
        y: y1,
        width: x2 - x1,
        height: y2 - y1,
    };
}

export function rectToBBox(x: number, y: number, w: number, h: number): [number, number, number, number] {
    return [Math.round(x), Math.round(y), Math.round(x + w), Math.round(y + h)];
}

export const REGION_COLORS: Record<string, string> = {
    speech: '#3b82f6', // blue-500
    sfx: '#eab308',    // yellow-500
    connect: '#22c55e', // green-500
    unknown: '#ef4444', // red-500
};

export function getRegionColor(type: string) {
    return REGION_COLORS[type] || REGION_COLORS.unknown;
}
