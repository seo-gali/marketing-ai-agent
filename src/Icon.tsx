import type { ReactNode } from 'react'

export default function Icon({name,size=18}:{name:string;size?:number}){
  const paths:Record<string,ReactNode>={
    grid:<><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></>,
    video:<><rect x="3" y="5" width="18" height="14" rx="3"/><path d="m10 9 5 3-5 3z"/></>,
    clock:<><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></>,
    settings:<><circle cx="12" cy="12" r="3"/><path d="M12 2v3m0 14v3M2 12h3m14 0h3M5 5l2.1 2.1M17 17l2 2M19 5l-2.1 2.1M7 17l-2 2"/></>,
    search:<><circle cx="11" cy="11" r="7"/><path d="m16 16 5 5"/></>,
    refresh:<><path d="M20 11a8 8 0 1 0-2 6"/><path d="M20 4v7h-7"/></>,
    link:<><path d="M10 13a5 5 0 0 0 7 .5l3-3a5 5 0 0 0-7-7l-2 2M14 11a5 5 0 0 0-7-.5l-3 3a5 5 0 0 0 7 7l2-2"/></>,
    chevron:<path d="m9 18 6-6-6-6"/>,
    sparkle:<><path d="m12 2 2.3 7.7L22 12l-7.7 2.3L12 22l-2.3-7.7L2 12l7.7-2.3z"/></>,
    check:<path d="m5 12 4 4L19 6"/>,
    alert:<><circle cx="12" cy="12" r="9"/><path d="M12 7v6m0 4h.01"/></>,
    external:<><path d="M13 4h7v7m0-7-9 9"/><path d="M19 13v7H4V5h7"/></>,
    copy:<><rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2"/></>,
    user:<><circle cx="12" cy="8" r="4"/><path d="M5 21c0-5 14-5 14 0"/></>,
    play:<path d="m8 5 12 7-12 7z"/>,
    shield:<><path d="M12 2 4 6v6c0 5 3 8 8 10 5-2 8-5 8-10V6z"/><path d="m8 12 3 3 5-6"/></>,
    plus:<path d="M12 5v14M5 12h14"/>,
    trash:<><path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7m4-7v7"/></>,
    sun:<><circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M19 5l-1.5 1.5m-11 11L5 19"/></>,
    moon:<path d="M20.9 13A9 9 0 0 1 11 3.1 9 9 0 1 0 20.9 13Z"/>,
  };
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]||paths.grid}</svg>;
}
