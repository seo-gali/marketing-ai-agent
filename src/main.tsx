import { Component, type ReactNode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import './style.css'

class ErrorBoundary extends Component<{children:ReactNode},{failed:boolean}> {
  state={failed:false}
  static getDerivedStateFromError() {return {failed:true}}
  render() {
    if(this.state.failed) return <main className="crash-page" role="alert"><h1>화면을 표시하지 못했습니다</h1><p>새로고침해 다시 시도하세요. 임시 저장된 초안은 브라우저에 남아 있습니다.</p><button className="btn primary" onClick={()=>location.reload()}>새로고침</button></main>
    return this.props.children
  }
}

createRoot(document.getElementById('root')!).render(<ErrorBoundary><App/></ErrorBoundary>)
