"use client";

import { useEffect, useRef, useState } from "react";

export default function Mermaid({ chart }: { chart: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const [svg, setSvg] = useState<string>("");

  useEffect(() => {
    const renderChart = async () => {
      try {
        const mermaid = (await import("mermaid")).default;
        mermaid.initialize({
          startOnLoad: false,
          theme: "base",
          themeVariables: {
            fontFamily: "inherit",
            primaryColor: "#f4f1eb",
            primaryTextColor: "#332922",
            primaryBorderColor: "#d5cdc4",
            lineColor: "#7d5a3c",
            secondaryColor: "#e6e1d8",
            tertiaryColor: "#f4f1eb",
          }
        });
        const id = `mermaid-${Math.random().toString(36).substring(7)}`;
        const { svg: renderSvg } = await mermaid.render(id, chart);
        setSvg(renderSvg);
      } catch (e) {
        console.error("Mermaid parsing error", e);
      }
    };
    renderChart();
  }, [chart]);

  if (!svg) {
    return (
      <div className="h-[120px] flex items-center justify-center text-muted-foreground animate-pulse text-sm">
        Loading Pipeline...
      </div>
    );
  }

  return (
    <div 
      ref={ref} 
      dangerouslySetInnerHTML={{ __html: svg }} 
      className="flex justify-center w-full [&_svg]:max-w-full [&_svg]:h-auto" 
    />
  );
}
