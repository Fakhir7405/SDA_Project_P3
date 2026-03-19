# This is the Main module that keeps the track of all queues and tell observers about its behaviour/working.

class PipelineTelemetry:
    """
This class is the Subject in the Observer pattern. 
It keeps the track of all three queues,sends updates to observers that are registered. 
It is implemented in main.py and given to the dashboard in order to generate real time telemetry data.
"""

    def __init__(self, raw_q, ver_q, proc_q, max_size):
        self.raw_q    = raw_q
        self.ver_q    = ver_q
        self.proc_q   = proc_q
        self.max_size = max_size
        self.observers = []

    def attach(self, observer):
    #To Add an observer so that it can receive updates. 
    #The observer must have an update(state: dict) method.
        self.observers.append(observer)

    def detach(self, observer):
        # To remove an observer so it no longer receives updates.
        self.observers.remove(observer)

    def safe_qsize(self, q):
      # On macOS, qsize() can fail with NotImplementedError.
       # So we used try/except to ensure that the monitor works safely on all platforms.
        try:
            return q.qsize()
        except (NotImplementedError, Exception):
            return 0

    def get_status(self, q_size):
        #To make sure max_size is not zero to avoid dividing by zero.
        if self.max_size <= 0:
            return "Green"
        ratio = q_size / self.max_size
        if ratio > 0.8:
            return "Red"
        if ratio > 0.5:
            return "Yellow"
        return "Green"

    def notify(self):
        """
This function checks the sizes of all queues,creates a dictionary. 
Then sends its status to each observer. 
It is called automatically at regular intervals by the timer in main.py.
"""
        state = {
            "raw_size":      self.safe_qsize(self.raw_q),
            "verified_size": self.safe_qsize(self.ver_q),
            "processed_size": self.safe_qsize(self.proc_q),
            "Raw":       self.get_status(self.safe_qsize(self.raw_q)),
            "Verified":  self.get_status(self.safe_qsize(self.ver_q)),
            "Processed": self.get_status(self.safe_qsize(self.proc_q)),
        }
        def notify_observer(obs):
            try:
                obs.update(state)
            except Exception as e:
                print(f"[Telemetry] ERROR notifying observer: {e}")

        list(map(notify_observer, self.observers))