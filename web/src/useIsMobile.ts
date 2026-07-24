import { useEffect, useState } from 'react'

/** True below the phone / small-tablet breakpoint (iPhone 15 Pro = 393px). */
export function useIsMobile(breakpoint = 640): boolean {
  const [mobile, setMobile] = useState(() =>
    typeof window !== 'undefined'
      ? window.matchMedia(`(max-width: ${breakpoint}px)`).matches
      : false,
  )

  useEffect(() => {
    const q = window.matchMedia(`(max-width: ${breakpoint}px)`)
    const onChange = () => setMobile(q.matches)
    onChange()
    q.addEventListener('change', onChange)
    return () => q.removeEventListener('change', onChange)
  }, [breakpoint])

  return mobile
}
