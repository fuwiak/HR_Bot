'use client'

import { useEffect } from 'react'

declare global {
  interface Window {
    mermaid: {
      initialize: (config: any) => void
      contentLoaded: () => void
    }
  }
}

export default function MermaidDiagram({ diagram }: { diagram: string }) {
  useEffect(() => {
    const script = document.createElement('script')
    script.src = 'https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js'
    script.onload = () => {
      if (window.mermaid) {
        window.mermaid.initialize({
          startOnLoad: true,
          theme: 'default',
          themeVariables: {
            primaryColor: '#1877f2',
            primaryTextColor: '#1c1e21',
            primaryBorderColor: '#1877f2',
            lineColor: '#8b9dc3',
            secondaryColor: '#f0f2f5',
            tertiaryColor: '#fff',
          },
        })
        window.mermaid.contentLoaded()
      }
    }
    document.body.appendChild(script)

    return () => {
      document.body.removeChild(script)
    }
  }, [])

  return <div className="mermaid">{diagram}</div>
}
















