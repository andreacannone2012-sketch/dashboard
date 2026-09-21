// Copia questo file come "config.js" (stessa cartella di index.html) per
// usare la dashboard SENZA alcun server, aprendo index.html a doppio clic.
//
// Perché serve: quando la pagina è aperta come file (file://), il browser
// blocca per sicurezza le richieste fetch() a services.json. Uno <script>
// invece funziona sempre, anche da file://: per questo la configurazione va
// scritta come JavaScript invece che come JSON puro.
//
// Struttura identica a services.json. Per l'icona puoi usare un'emoji oppure
// un link (anche a un SVG) - un URL completo, un percorso assoluto o relativo
// con estensione (.svg, .png...), oppure un data URI.
window.NAS_CONFIG = {
  title: "Il mio NAS",
  name: "",
  services: [
    {
      name: "CasaOS",
      desc: "Pannello di controllo del server",
      icon: "🏠",
      port: 80,
      category: "Sistema"
    },
    {
      name: "LM Studio",
      desc: "Modelli linguistici in locale",
      icon: "🧠",
      port: 10021,
      category: "AI"
    },
    {
      name: "File WebDAV",
      desc: "Cartella condivisa Storage",
      icon: "📁",
      port: 5005,
      category: "File"
    },
    {
      name: "Servizio con icona da link",
      desc: "Esempio di icona SVG caricata da un URL",
      icon: "https://cdn.simpleicons.org/nginx",
      url: "http://192.168.1.10:8081",
      category: "Esempio"
    }
  ]
};
