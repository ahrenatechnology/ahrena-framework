export async function run(rows: string[]): Promise<void> {
  for (const row of rows) {
    await save(row);
  }
}
