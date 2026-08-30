import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Hybrid RAG · Document Assistant",
  description: "A grounded document workspace for answers you can inspect.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
