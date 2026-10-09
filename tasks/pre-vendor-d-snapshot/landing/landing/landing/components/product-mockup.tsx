export default function ProductMockup() {
  return (
    <div className="product-mockup" aria-label="Vismarttech platform preview">
      <div className="mockup-topbar">
        <span />
        <span />
        <span />
        <strong>Workflow Console</strong>
      </div>

      <div className="mockup-grid">
        <section className="mockup-panel mockup-main">
          <div className="mockup-node node-primary">Lead intent</div>
          <div className="mockup-line" />
          <div className="mockup-node">Knowledge RAG</div>
          <div className="mockup-line" />
          <div className="mockup-node node-success">CRM action</div>
        </section>

        <aside className="mockup-panel">
          <p className="mockup-label">Live quality</p>
          <div className="mockup-score">98.4%</div>
          <div className="mockup-bar"><span style={{ width: '84%' }} /></div>
          <div className="mockup-bar"><span style={{ width: '68%' }} /></div>
          <div className="mockup-bar"><span style={{ width: '76%' }} /></div>
        </aside>
      </div>

      <div className="mockup-chat">
        <div>
          <p className="mockup-label">Omnichannel assistant</p>
          <strong>Khách cần tư vấn gói Team</strong>
        </div>
        <span>Auto route</span>
      </div>
    </div>
  )
}
