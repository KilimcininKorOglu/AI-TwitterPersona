import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI-TwitterPersona | Otonom Twitter Asistanı",
  description: "Yapay zeka destekli otonom Twitter bot yönetim paneli",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="tr">
      <head>
        <link rel="icon" href="/favicon.svg" type="image/svg+xml" />
      </head>
      <body className="font-sans antialiased">
        {children}
      </body>
    </html>
  );
}
