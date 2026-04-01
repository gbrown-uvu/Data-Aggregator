import customtkinter as CTk

class MaskEntry(CTk.CTkEntry):
    """CTkEntry that always displays a fixed number of asterisks when masked,
       regardless of the actual text length."""
    
    def __init__(self, master, mask_length: int = 15, **kwargs):
        super().__init__(master, **kwargs)
        self.mask_length = mask_length
        self._real_text = ""          # stores the actual value
        self._is_masked = True
        
        # Bind to detect changes (typing, paste, delete, etc.)
        self.bind("<KeyRelease>", self._on_change)
        self.bind("<FocusOut>", self._on_change)
        
        # Initial display
        self._update_display()

    def _on_change(self, event=None):
        if not self._is_masked:
            self._real_text = self.get()
        self._update_display()

    def _update_display(self):
        if self._is_masked:
            # Always show exactly mask_length asterisks
            display_text = "*" * self.mask_length
            # Temporarily disable the show="" so we can set the fake text
            self.configure(show="")
            self.delete(0, "end")
            self.insert(0, display_text)
            self.configure(show="*")  # re-enable masking if needed, but we override anyway
        else:
            # Show real text
            self.configure(show="")
            self.delete(0, "end")
            self.insert(0, self._real_text)

    def get_real(self) -> str:
        """Return the actual value (use this instead of .get() when you need the real data)."""
        return self._real_text

    def set_real(self, text: str):
        """Set the real value programmatically."""
        self._real_text = text
        self._update_display()

    def toggle_mask(self):
        """Switch between masked and real view."""
        self._is_masked = not self._is_masked
        self._update_display()