"""
Reddit Bot - Admin Panel
Professional GUI for managing users, viewing stats, and monitoring usage.
"""
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from datetime import datetime
from database import Database
from admin_tools import AdminTools
import threading

class AdminPanel:
    def __init__(self, root):
        self.root = root
        self.root.title("Reddit Bot - Admin Panel")
        self.root.geometry("1200x800")
        self.center_window()
        
        # Initialize database and admin tools
        try:
            self.db = Database()
            self.admin = AdminTools()
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to connect to database:\n{str(e)}")
            root.destroy()
            return
        
        self.setup_ui()
        self.refresh_users_list()
    
    def center_window(self):
        """Center the window on screen."""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    def setup_ui(self):
        """Setup admin panel UI."""
        # Top menu bar
        menu_frame = tk.Frame(self.root, bg="#2c3e50", height=60)
        menu_frame.pack(fill=tk.X)
        menu_frame.pack_propagate(False)
        
        title_label = tk.Label(
            menu_frame,
            text="Reddit Bot - Admin Panel",
            font=("Arial", 18, "bold"),
            bg="#2c3e50",
            fg="white"
        )
        title_label.pack(side=tk.LEFT, padx=20, pady=15)
        
        refresh_btn = tk.Button(
            menu_frame,
            text="🔄 Refresh",
            command=self.refresh_users_list,
            bg="#3498db",
            fg="white",
            font=("Arial", 10, "bold"),
            cursor="hand2",
            padx=10
        )
        refresh_btn.pack(side=tk.RIGHT, padx=10, pady=10)
        
        # Main container
        main_container = tk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left panel - Actions
        left_panel = tk.Frame(main_container, width=300)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 10))
        left_panel.pack_propagate(False)
        
        # Create User Section
        create_frame = ttk.LabelFrame(left_panel, text="Create New User", padding=15)
        create_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(create_frame, text="Password:", font=("Arial", 9)).pack(anchor=tk.W, pady=5)
        self.new_password_entry = tk.Entry(create_frame, font=("Arial", 10), show="*", width=25)
        self.new_password_entry.pack(fill=tk.X, pady=5)
        
        tk.Label(create_frame, text="Notes (optional):", font=("Arial", 9)).pack(anchor=tk.W, pady=5)
        self.new_notes_entry = tk.Entry(create_frame, font=("Arial", 10), width=25)
        self.new_notes_entry.pack(fill=tk.X, pady=5)
        
        create_btn = tk.Button(
            create_frame,
            text="Create User",
            command=self.create_user,
            bg="#27ae60",
            fg="white",
            font=("Arial", 10, "bold"),
            width=20,
            cursor="hand2"
        )
        create_btn.pack(pady=10)
        
        # User Actions Section
        actions_frame = ttk.LabelFrame(left_panel, text="User Actions", padding=15)
        actions_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.selected_license_key = tk.StringVar()
        
        tk.Label(actions_frame, text="Selected License Key:", font=("Arial", 9)).pack(anchor=tk.W, pady=5)
        selected_entry = tk.Entry(actions_frame, textvariable=self.selected_license_key, 
                                  font=("Arial", 9), state="readonly", width=25)
        selected_entry.pack(fill=tk.X, pady=5)
        
        view_stats_btn = tk.Button(
            actions_frame,
            text="View Statistics",
            command=self.view_user_stats,
            bg="#3498db",
            fg="white",
            font=("Arial", 9, "bold"),
            width=20,
            cursor="hand2"
        )
        view_stats_btn.pack(pady=5)
        
        deactivate_btn = tk.Button(
            actions_frame,
            text="Deactivate User",
            command=self.deactivate_user,
            bg="#e74c3c",
            fg="white",
            font=("Arial", 9, "bold"),
            width=20,
            cursor="hand2"
        )
        deactivate_btn.pack(pady=5)
        
        activate_btn = tk.Button(
            actions_frame,
            text="Activate User",
            command=self.activate_user,
            bg="#27ae60",
            fg="white",
            font=("Arial", 9, "bold"),
            width=20,
            cursor="hand2"
        )
        activate_btn.pack(pady=5)
        
        view_creds_btn = tk.Button(
            actions_frame,
            text="View Credentials",
            command=self.view_credentials,
            bg="#9b59b6",
            fg="white",
            font=("Arial", 9, "bold"),
            width=20,
            cursor="hand2"
        )
        view_creds_btn.pack(pady=5)
        
        delete_btn = tk.Button(
            actions_frame,
            text="Delete User",
            command=self.delete_user,
            bg="#c0392b",
            fg="white",
            font=("Arial", 9, "bold"),
            width=20,
            cursor="hand2"
        )
        delete_btn.pack(pady=5)
        
        # Statistics Section
        stats_frame = ttk.LabelFrame(left_panel, text="Overall Statistics", padding=15)
        stats_frame.pack(fill=tk.BOTH, expand=True)
        
        self.stats_text = tk.Text(stats_frame, height=10, font=("Arial", 9), wrap=tk.WORD)
        self.stats_text.pack(fill=tk.BOTH, expand=True)
        self.update_overall_stats()
        
        # Right panel - Users List
        right_panel = tk.Frame(main_container)
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Search frame
        search_frame = tk.Frame(right_panel)
        search_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(search_frame, text="Search:", font=("Arial", 10)).pack(side=tk.LEFT, padx=5)
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self.filter_users)
        search_entry = tk.Entry(search_frame, textvariable=self.search_var, font=("Arial", 10), width=30)
        search_entry.pack(side=tk.LEFT, padx=5)
        
        # Users table
        table_frame = tk.Frame(right_panel)
        table_frame.pack(fill=tk.BOTH, expand=True)
        
        # Treeview for users
        columns = ("License Key", "Status", "Sessions", "Accounts", "Last Login", "Activated", "IP")
        self.users_tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=20)
        
        # Configure columns
        self.users_tree.heading("License Key", text="License Key")
        self.users_tree.heading("Status", text="Status")
        self.users_tree.heading("Sessions", text="Sessions")
        self.users_tree.heading("Accounts", text="Accounts Processed")
        self.users_tree.heading("Last Login", text="Last Login")
        self.users_tree.heading("Activated", text="Activated")
        self.users_tree.heading("IP", text="IP Address")
        
        self.users_tree.column("License Key", width=200)
        self.users_tree.column("Status", width=80)
        self.users_tree.column("Sessions", width=80)
        self.users_tree.column("Accounts", width=120)
        self.users_tree.column("Last Login", width=150)
        self.users_tree.column("Activated", width=150)
        self.users_tree.column("IP", width=120)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.users_tree.yview)
        h_scrollbar = ttk.Scrollbar(table_frame, orient="horizontal", command=self.users_tree.xview)
        self.users_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        self.users_tree.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        
        # Bind selection
        self.users_tree.bind('<<TreeviewSelect>>', self.on_user_select)
        
        # Double-click to view stats
        self.users_tree.bind('<Double-1>', lambda e: self.view_user_stats())
    
    def refresh_users_list(self):
        """Refresh the users list."""
        # Clear existing items
        for item in self.users_tree.get_children():
            self.users_tree.delete(item)
        
        try:
            users = self.admin.list_users()
            
            for user in users:
                status = "✅ Active" if user.get('is_active') else "❌ Inactive"
                last_login = user.get('last_login', '') or 'Never'
                if last_login != 'Never':
                    try:
                        dt = datetime.fromisoformat(last_login.replace('Z', '+00:00'))
                        last_login = dt.strftime('%Y-%m-%d %H:%M')
                    except:
                        pass
                
                activated = user.get('activated_at', '') or 'Not activated'
                if activated != 'Not activated':
                    try:
                        dt = datetime.fromisoformat(activated.replace('Z', '+00:00'))
                        activated = dt.strftime('%Y-%m-%d %H:%M')
                    except:
                        pass
                
                ip = user.get('activation_ip', '') or 'N/A'
                if ip and ip != '0.0.0.0':
                    ip = str(ip)
                else:
                    ip = 'N/A'
                
                self.users_tree.insert("", "end", values=(
                    user.get('license_key', ''),
                    status,
                    user.get('total_sessions', 0),
                    user.get('total_accounts_processed', 0),
                    last_login,
                    activated,
                    ip
                ))
            
            self.update_overall_stats()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load users: {str(e)}")
    
    def filter_users(self, *args):
        """Filter users based on search."""
        search_term = self.search_var.get().lower()
        
        for item in self.users_tree.get_children():
            values = self.users_tree.item(item, 'values')
            if search_term in ' '.join(str(v).lower() for v in values):
                self.users_tree.item(item, tags=('visible',))
            else:
                self.users_tree.item(item, tags=('hidden',))
        
        # Hide filtered items
        for item in self.users_tree.get_children():
            if 'hidden' in self.users_tree.item(item, 'tags'):
                self.users_tree.detach(item)
            else:
                self.users_tree.reattach(item, '', 'end')
    
    def on_user_select(self, event):
        """Handle user selection."""
        selection = self.users_tree.selection()
        if selection:
            item = self.users_tree.item(selection[0])
            license_key = item['values'][0]
            self.selected_license_key.set(license_key)
    
    def create_user(self):
        """Create a new user."""
        password = self.new_password_entry.get().strip()
        notes = self.new_notes_entry.get().strip()
        
        if not password:
            messagebox.showwarning("Warning", "Please enter a password")
            return
        
        try:
            license_key, activation_code, success, error = self.admin.create_user(password, notes)
            
            if success:
                # Show credentials in a message box
                creds_window = tk.Toplevel(self.root)
                creds_window.title("User Created - Save Credentials")
                creds_window.geometry("500x300")
                creds_window.transient(self.root)
                creds_window.grab_set()
                
                # Center window
                creds_window.update_idletasks()
                x = (creds_window.winfo_screenwidth() // 2) - (500 // 2)
                y = (creds_window.winfo_screenheight() // 2) - (300 // 2)
                creds_window.geometry(f'500x300+{x}+{y}')
                
                main_frame = tk.Frame(creds_window, padx=30, pady=30)
                main_frame.pack(fill=tk.BOTH, expand=True)
                
                tk.Label(main_frame, text="✅ User Created Successfully!", 
                        font=("Arial", 14, "bold"), fg="green").pack(pady=10)
                
                tk.Label(main_frame, text="Save these credentials:", 
                        font=("Arial", 11, "bold")).pack(pady=10)
                
                # Credentials display
                creds_text = scrolledtext.ScrolledText(main_frame, height=8, font=("Consolas", 10), wrap=tk.WORD)
                creds_text.pack(fill=tk.BOTH, expand=True, pady=10)
                creds_text.insert(1.0, f"License Key: {license_key}\n")
                creds_text.insert(tk.END, f"Password: {password}\n")
                creds_text.insert(tk.END, f"Activation Code: {activation_code}\n")
                creds_text.config(state=tk.DISABLED)
                
                tk.Button(main_frame, text="Close", command=creds_window.destroy,
                         bg="#3498db", fg="white", font=("Arial", 10, "bold"),
                         width=15, cursor="hand2").pack(pady=10)
                
                # Clear fields
                self.new_password_entry.delete(0, tk.END)
                self.new_notes_entry.delete(0, tk.END)
                
                # Refresh list
                self.refresh_users_list()
            else:
                messagebox.showerror("Error", f"Failed to create user: {error}")
        except Exception as e:
            messagebox.showerror("Error", f"Error creating user: {str(e)}")
    
    def view_user_stats(self):
        """View detailed statistics for selected user."""
        license_key = self.selected_license_key.get().strip()
        
        if not license_key:
            messagebox.showwarning("Warning", "Please select a user first")
            return
        
        try:
            stats = self.admin.get_user_stats(license_key)
            
            if not stats:
                messagebox.showwarning("Warning", "User not found")
                return
            
            user = stats['user']
            sessions = stats.get('recent_sessions', [])
            
            # Create stats window
            stats_window = tk.Toplevel(self.root)
            stats_window.title(f"User Statistics - {license_key}")
            stats_window.geometry("700x600")
            stats_window.transient(self.root)
            
            # Center window
            stats_window.update_idletasks()
            x = (stats_window.winfo_screenwidth() // 2) - (700 // 2)
            y = (stats_window.winfo_screenheight() // 2) - (600 // 2)
            stats_window.geometry(f'700x600+{x}+{y}')
            
            main_frame = tk.Frame(stats_window, padx=20, pady=20)
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # User info
            info_frame = ttk.LabelFrame(main_frame, text="User Information", padding=15)
            info_frame.pack(fill=tk.X, pady=(0, 10))
            
            info_text = f"""
License Key: {user.get('license_key', 'N/A')}
Status: {'✅ Active' if user.get('is_active') else '❌ Inactive'}
Total Sessions: {user.get('total_sessions', 0)}
Total Accounts Processed: {user.get('total_accounts_processed', 0)}
Activation IP: {user.get('activation_ip', 'N/A')}
Last Login: {user.get('last_login', 'Never') or 'Never'}
Activated At: {user.get('activated_at', 'Not activated') or 'Not activated'}
Created At: {user.get('created_at', 'N/A')}
Notes: {user.get('notes', 'N/A')}
"""
            
            tk.Label(info_frame, text=info_text, font=("Arial", 10), 
                    justify=tk.LEFT, anchor=tk.W).pack(fill=tk.X)
            
            # Recent sessions
            sessions_frame = ttk.LabelFrame(main_frame, text="Recent Sessions", padding=15)
            sessions_frame.pack(fill=tk.BOTH, expand=True)
            
            if sessions:
                # Create table for sessions
                sessions_tree = ttk.Treeview(sessions_frame, columns=("Date", "Accounts", "Success", "Invalid", "Banned", "Errors", "Duration"), 
                                            show="headings", height=10)
                
                sessions_tree.heading("Date", text="Date")
                sessions_tree.heading("Accounts", text="Accounts")
                sessions_tree.heading("Success", text="Success")
                sessions_tree.heading("Invalid", text="Invalid")
                sessions_tree.heading("Banned", text="Banned")
                sessions_tree.heading("Errors", text="Errors")
                sessions_tree.heading("Duration", text="Duration (sec)")
                
                for session in sessions[:20]:  # Show last 20 sessions
                    date = session.get('session_start', '')
                    if date:
                        try:
                            dt = datetime.fromisoformat(date.replace('Z', '+00:00'))
                            date = dt.strftime('%Y-%m-%d %H:%M:%S')
                        except:
                            pass
                    
                    duration = session.get('duration_seconds', 0) or 0
                    
                    sessions_tree.insert("", "end", values=(
                        date,
                        session.get('accounts_processed', 0),
                        session.get('success_count', 0),
                        session.get('invalid_count', 0),
                        session.get('banned_count', 0),
                        session.get('error_count', 0),
                        duration
                    ))
                
                sessions_tree.pack(fill=tk.BOTH, expand=True)
            else:
                tk.Label(sessions_frame, text="No sessions found", 
                        font=("Arial", 10), fg="gray").pack(pady=20)
            
            tk.Button(main_frame, text="Close", command=stats_window.destroy,
                     bg="#3498db", fg="white", font=("Arial", 10, "bold"),
                     width=15, cursor="hand2").pack(pady=10)
            
        except Exception as e:
            messagebox.showerror("Error", f"Error loading stats: {str(e)}")
    
    def deactivate_user(self):
        """Deactivate selected user."""
        license_key = self.selected_license_key.get().strip()
        
        if not license_key:
            messagebox.showwarning("Warning", "Please select a user first")
            return
        
        if not messagebox.askyesno("Confirm", f"Deactivate user {license_key}?"):
            return
        
        try:
            success, error = self.admin.deactivate_user(license_key)
            if success:
                messagebox.showinfo("Success", "User deactivated successfully")
                self.refresh_users_list()
            else:
                messagebox.showerror("Error", f"Failed to deactivate: {error}")
        except Exception as e:
            messagebox.showerror("Error", f"Error: {str(e)}")
    
    def activate_user(self):
        """Activate selected user (admin override)."""
        license_key = self.selected_license_key.get().strip()
        
        if not license_key:
            messagebox.showwarning("Warning", "Please select a user first")
            return
        
        try:
            # Direct database update to activate
            self.db.client.table('users').update({
                'is_active': True
            }).eq('license_key', license_key).execute()
            
            messagebox.showinfo("Success", "User activated successfully")
            self.refresh_users_list()
        except Exception as e:
            messagebox.showerror("Error", f"Error: {str(e)}")
    
    def view_credentials(self):
        """View user credentials (password, license key, activation code)."""
        license_key = self.selected_license_key.get().strip()
        
        if not license_key:
            messagebox.showwarning("Warning", "Please select a user first")
            return
        
        try:
            # Get user data
            user_result = self.db.client.table('users').select('*').eq('license_key', license_key).execute()
            if not user_result.data:
                messagebox.showwarning("Warning", "User not found")
                return
            
            user = user_result.data[0]
            
            # Get activation code
            activation_result = self.db.client.table('activations').select('*').eq('license_key', license_key).execute()
            activation_code = "N/A"
            if activation_result.data:
                activation_code = activation_result.data[0].get('activation_code', 'N/A')
            
            # We can't decrypt password, but we can show the hash and let admin reset it
            # For security, we'll need to get the original password from admin_tools or allow reset
            
            # Create credentials window
            creds_window = tk.Toplevel(self.root)
            creds_window.title(f"User Credentials - {license_key}")
            creds_window.geometry("500x400")
            creds_window.transient(self.root)
            creds_window.grab_set()
            
            # Center window
            creds_window.update_idletasks()
            x = (creds_window.winfo_screenwidth() // 2) - (500 // 2)
            y = (creds_window.winfo_screenheight() // 2) - (400 // 2)
            creds_window.geometry(f'500x400+{x}+{y}')
            
            main_frame = tk.Frame(creds_window, padx=30, pady=30)
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            tk.Label(main_frame, text="User Credentials", 
                    font=("Arial", 14, "bold")).pack(pady=10)
            
            tk.Label(main_frame, text="⚠️ Passwords are encrypted and cannot be retrieved.", 
                    font=("Arial", 9), fg="red").pack(pady=5)
            tk.Label(main_frame, text="You can reset the password below.", 
                    font=("Arial", 9), fg="gray").pack(pady=(0, 15))
            
            # Credentials display
            creds_text = scrolledtext.ScrolledText(main_frame, height=12, font=("Consolas", 10), wrap=tk.WORD)
            creds_text.pack(fill=tk.BOTH, expand=True, pady=10)
            
            creds_info = f"""License Key: {license_key}
Activation Code: {activation_code}
Status: {'Active' if user.get('is_active') else 'Inactive'}
IP Address: {user.get('activation_ip', 'N/A')}
Created: {user.get('created_at', 'N/A')}
Activated: {user.get('activated_at', 'Not activated') or 'Not activated'}
Last Login: {user.get('last_login', 'Never') or 'Never'}
Total Sessions: {user.get('total_sessions', 0)}
Total Accounts: {user.get('total_accounts_processed', 0)}
Notes: {user.get('notes', 'N/A')}

⚠️ Password: Cannot be retrieved (encrypted)
   Use "Reset Password" below to set a new password.
"""
            creds_text.insert(1.0, creds_info)
            creds_text.config(state=tk.DISABLED)
            
            # Reset password section
            reset_frame = tk.Frame(main_frame)
            reset_frame.pack(fill=tk.X, pady=10)
            
            tk.Label(reset_frame, text="Reset Password:", font=("Arial", 9)).pack(side=tk.LEFT, padx=5)
            new_pass_entry = tk.Entry(reset_frame, font=("Arial", 10), show="*", width=20)
            new_pass_entry.pack(side=tk.LEFT, padx=5)
            
            def reset_password():
                new_pass = new_pass_entry.get().strip()
                if not new_pass:
                    messagebox.showwarning("Warning", "Please enter a new password")
                    return
                
                if not messagebox.askyesno("Confirm", f"Reset password for {license_key}?"):
                    return
                
                try:
                    # Hash and update password
                    password_hash = self.admin.hash_password(new_pass)
                    self.db.client.table('users').update({
                        'password_hash': password_hash
                    }).eq('license_key', license_key).execute()
                    
                    messagebox.showinfo("Success", f"Password reset successfully!\n\nNew Password: {new_pass}\n\nShare this with the user.")
                    creds_window.destroy()
                except Exception as e:
                    messagebox.showerror("Error", f"Error resetting password: {str(e)}")
            
            tk.Button(reset_frame, text="Reset", command=reset_password,
                     bg="#e67e22", fg="white", font=("Arial", 9, "bold"),
                     cursor="hand2").pack(side=tk.LEFT, padx=5)
            
            tk.Button(main_frame, text="Close", command=creds_window.destroy,
                     bg="#3498db", fg="white", font=("Arial", 10, "bold"),
                     width=15, cursor="hand2").pack(pady=10)
            
        except Exception as e:
            messagebox.showerror("Error", f"Error loading credentials: {str(e)}")
    
    def delete_user(self):
        """Delete selected user (permanent)."""
        license_key = self.selected_license_key.get().strip()
        
        if not license_key:
            messagebox.showwarning("Warning", "Please select a user first")
            return
        
        # Double confirmation
        if not messagebox.askyesno("Confirm Deletion", 
                                  f"Are you sure you want to DELETE user {license_key}?\n\n"
                                  "This will permanently delete:\n"
                                  "- User account\n"
                                  "- All usage logs\n"
                                  "- All session details\n"
                                  "- Activation records\n\n"
                                  "This action CANNOT be undone!"):
            return
        
        if not messagebox.askyesno("Final Confirmation", 
                                  f"FINAL WARNING: Delete {license_key}?\n\n"
                                  "This is permanent and cannot be undone!"):
            return
        
        try:
            # Get user ID first
            user_result = self.db.client.table('users').select('id').eq('license_key', license_key).execute()
            if not user_result.data:
                messagebox.showwarning("Warning", "User not found")
                return
            
            user_id = user_result.data[0]['id']
            
            # Delete user (cascade will delete related records)
            self.db.client.table('users').delete().eq('id', user_id).execute()
            
            messagebox.showinfo("Success", "User deleted successfully")
            self.selected_license_key.set("")
            self.refresh_users_list()
        except Exception as e:
            messagebox.showerror("Error", f"Error deleting user: {str(e)}")
    
    def update_overall_stats(self):
        """Update overall statistics."""
        try:
            users = self.admin.list_users()
            
            total_users = len(users)
            active_users = sum(1 for u in users if u.get('is_active'))
            total_sessions = sum(u.get('total_sessions', 0) for u in users)
            total_accounts = sum(u.get('total_accounts_processed', 0) for u in users)
            
            self.stats_text.delete(1.0, tk.END)
            stats_content = f"""Total Users: {total_users}
Active Users: {active_users}
Inactive Users: {total_users - active_users}
Total Sessions: {total_sessions}
Total Accounts Processed: {total_accounts}
"""
            self.stats_text.insert(1.0, stats_content)
        except:
            pass


def main():
    """Main entry point."""
    root = tk.Tk()
    app = AdminPanel(root)
    root.mainloop()


if __name__ == "__main__":
    main()

