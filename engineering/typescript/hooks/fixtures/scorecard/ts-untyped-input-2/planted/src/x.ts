type Order = { id: string };
export const x = (raw: string): Order => JSON.parse(raw) as Order;
