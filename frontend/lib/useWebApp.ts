'use client'

import { useEffect, useState } from 'react'

let WebAppInstance: any = null

export function useWebApp() {
  const [webApp, setWebApp] = useState<any>(null)

  useEffect(() => {
    if (typeof window !== 'undefined' && !WebAppInstance) {
      import('@twa-dev/sdk').then((module) => {
        WebAppInstance = module.default
        setWebApp(WebAppInstance)
      })
    } else if (WebAppInstance) {
      setWebApp(WebAppInstance)
    }
  }, [])

  return webApp
}
