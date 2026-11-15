export function run(rows: string[]): void {
  rows.forEach(async (row) => {
    await save(row);
  });
}
