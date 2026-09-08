export async function GET() {
  return new Response(JSON.stringify({ message: "OK" }), {
    headers: { "Content-Type": "application/json" },
  });
}