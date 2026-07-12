import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";

const caskaydiaCove = localFont({
  src: "../../public/fonts/CaskaydiaCoveNerdFont-Regular.ttf",
  variable: "--font-caskaydia-cove",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Helios",
  description: "Autonomous AI Software Company - One Prompt, One Company, One Product",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${caskaydiaCove.variable} font-sans antialiased`}
      >
        {children}
      </body>
    </html>
  );
}
