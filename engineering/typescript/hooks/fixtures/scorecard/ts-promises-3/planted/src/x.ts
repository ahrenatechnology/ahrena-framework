export async function run(): Promise<void> {
  try {
    await save();
  } catch (error) {}
}
