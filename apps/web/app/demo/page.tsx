import type { Metadata } from "next";
import DemoPage from "@/components/demo-page";

export const metadata: Metadata = {
  title: "Demo — BosesPH Toolkit",
  description: "Try live Kapampangan speech transcription with BosesPH",
};

export default function Demo() {
  return <DemoPage />;
}
