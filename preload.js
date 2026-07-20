const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  reiniciarApp: () => ipcRenderer.send('reiniciar-app'),
  actualizarSistema: () => ipcRenderer.invoke('actualizar-sistema'),
  onActualizarProgreso: (callback) => {
    ipcRenderer.removeAllListeners('actualizar-sistema-progreso');
    ipcRenderer.on('actualizar-sistema-progreso', (_event, mensaje) => callback(mensaje));
  }
});
