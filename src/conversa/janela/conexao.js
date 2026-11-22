"use strict";
// WebRTC à mão (sem cliente do pipecat) e canal de dados do RTVI. Nada vem da internet.
window.GroovConexao = (function () {
  let pc = null, canal = null, ping = null, reconectando = false, substituida = false;
  let ganchos = {};

  function esperarCandidatos(conexao) {
    // Sem trickle: no localhost a coleta termina na hora e dispensa o PATCH /api/offer.
    if (conexao.iceGatheringState === "complete") return Promise.resolve();
    return new Promise((ok) => {
      const fim = setTimeout(ok, 3000);
      conexao.addEventListener("icegatheringstatechange", () => {
        if (conexao.iceGatheringState === "complete") { clearTimeout(fim); ok(); }
      });
    });
  }

  async function conectar() {
    const microfone = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
    });
    const conexao = pc = new RTCPeerConnection();
    conexao.addTransceiver(microfone.getAudioTracks()[0], { direction: "sendrecv" });
    conexao.ontrack = (e) => { document.getElementById("saida").srcObject = e.streams[0]; };

    const novo = canal = conexao.createDataChannel("chat", { ordered: true });
    novo.onopen = () => {
      novo.send(JSON.stringify({
        label: "rtvi-ai", type: "client-ready", id: crypto.randomUUID(),
        data: { version: "2.2.0", about: { library: "groov-janela", library_version: "1" } },
      }));
      ping = setInterval(() => { if (novo.readyState === "open") novo.send("ping"); }, 1000);
    };
    novo.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data);
        // o servidor só tem uma conexão: outra janela/aba pediu a vez e o pipecat avisa com peerLeft
        if (msg.type === "signalling" && msg.message && msg.message.type === "peerLeft") substituida = true;
        if (msg.label === "rtvi-ai") ganchos.aoMensagem(msg);
      } catch { /* mensagens de sinalização do pipecat não interessam à janela */ }
    };
    conexao.onconnectionstatechange = () => {
      if (["failed", "disconnected", "closed"].includes(conexao.connectionState)) reconectar(conexao);
    };

    await conexao.setLocalDescription(await conexao.createOffer());
    await esperarCandidatos(conexao);
    const resposta = await fetch("/api/offer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sdp: conexao.localDescription.sdp, type: conexao.localDescription.type }),
    });
    if (!resposta.ok) throw new Error(`/api/offer ${resposta.status}`);
    await conexao.setRemoteDescription(await resposta.json());
  }

  function fechar() {
    clearInterval(ping);
    if (pc) { pc.onconnectionstatechange = null; pc.getSenders().forEach((s) => s.track && s.track.stop()); pc.close(); }
    pc = canal = null;
  }

  function reconectar(conexao) {
    if (reconectando || conexao !== pc) return;
    fechar();
    ganchos.aoCair();
    if (substituida) { ganchos.aoSubstituida(); return; }  // sem reconectar: as duas janelas ficariam se derrubando sem parar
    reconectando = true;
    setTimeout(() => { reconectando = false; tentar(); }, 2000);
  }

  async function tentar() {
    try {
      await conectar();
    } catch (erro) {
      console.error(erro);
      ganchos.aoErro(erro);
      fechar();
      reconectando = true;
      setTimeout(() => { reconectando = false; tentar(); }, 4000);
    }
  }

  function enviar(t, d) {
    if (!canal || canal.readyState !== "open") return false;
    canal.send(JSON.stringify({ label: "rtvi-ai", type: "client-message", id: crypto.randomUUID(), data: { t, d } }));
    return true;
  }

  function iniciar({ aoMensagem, aoCair, aoSubstituida, aoErro }) {
    ganchos = { aoMensagem, aoCair, aoSubstituida, aoErro };
    tentar();
    return { enviar };
  }

  return { iniciar };
})();
