import threading
import time

class TeleportHandler():
    def __init__(self, app):
        self.app = app

        self.running = False

        self.thread = None

        self.events = []
    
    def add_event(self, event):
        self.events.append(event)
    
    def _process(self):
        time.sleep(1 / self.app.fps)
    
    def start(self):
        if self.thread != None: return

        self.running = True

        def worker():
            while self.running:
                try:
                    while self.running:
                        if self.app.datamodel and self.app.datamodel.get_gameloaded():
                            break
                        self._process()
                            
                    if not self.running:
                        break

                    for event in self.events:
                        event()
                    self.events.clear()

                    prevdm_name = self.app.datamodel.get_name()
                        
                    while self.running:
                        if not self.app.datamodel or self.app.datamodel.get_name() != prevdm_name or not self.app.datamodel.get_gameloaded():
                            break
                        self._process()
                    
                    if not self.running:
                        break
                except Exception:
                    pass

        self.thread = threading.Thread(target=worker, daemon=True)
        self.thread.start()
            
    def stop(self):
        if self.thread == None: return

        self.running = False

        self.thread = None
        self.events.clear()