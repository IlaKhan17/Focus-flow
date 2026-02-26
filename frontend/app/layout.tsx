import "./globals.css";

export const metadata = {
  title: "Focus Flow",
  description: "AI-powered deep work assistant",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="ff-body">
        <div className="ff-shell">{children}</div>
      </body>
    </html>
  );
}
