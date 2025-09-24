# Application Toolkit Pro

**Author:** KarexiDEV

A comprehensive and powerful application manager for Windows, designed to provide detailed insights and easy management of installed software, including Win32 applications, UWP (Microsoft Store) apps, and portable programs.

---

## ✨ Key Features

* **All-in-One Dashboard:** View all your installed Win32, UWP, and scanned portable applications in a clean, tabbed interface.
* **Smart Categorization:** Automatically sorts programs into 'Applications' and 'Games' for better organization.
* **Advanced Filtering:** Quickly find any application by searching for its name or publisher. Further refine results by installation date, size, architecture (64-bit/32-bit), or installation drive.
* **Detailed Information Panel:** Select any application to see in-depth details like version, publisher, installation date, estimated size, full path, and associated registry key.
* **Powerful Uninstaller:** Uninstall one or multiple programs at once. Includes a **"Try Silent Uninstall"** option to attempt an automated, non-interactive removal.
* **Portable App Scanner:** Scan any folder on your system to find and list portable applications that don't appear in the standard Windows program list.
* **Favorites System:** Mark important applications as favorites for quick access in a dedicated tab.
* **Windows Integration:**
    * **Context Menu:** Add an "Uninstall Program" option to the right-click menu of shortcuts (.lnk files) for quick removal (Requires Admin rights).
    * **System Tray:** The application can be minimized to the system tray to run unobtrusively in the background.

### 💡 About Application/Game Classification

The program distinguishes between the 'Applications' and 'Games' tabs using a local method based on keywords found in application names and publishers. While this method works correctly for most popular software, it may occasionally result in incorrect classifications.

The original version of this project included a more advanced classification system, but it relied on an external server. This dependency was removed to ensure the open-source version is fully self-contained, transparent, and can run offline.

**How You Can Help**
Improving this classification logic is one of the most valuable contributions you can make to the project. You can help by examining the `classify_program` function in `apc.py` to add more keywords, suggest a smarter local classification logic, or by opening an "issue" to share your ideas.

---

## 📦 Installation (For End-Users)

1.  Download the latest `ApplicationToolkitPro-x.x.x.exe` installer from the project's [Releases](https://github.com/KarexiDEV/ApplicationToolkitPro/releases) page.
2.  Follow the on-screen instructions to complete the installation.
3.  That's it! You can now launch the program.

---

## 💻 For Developers (Running from Source)

To run this program from the source code:

1.  Clone this repository:
    ```sh
    git clone [https://github.com/KarexiDEV/ApplicationToolkitPro.git](https://github.com/KarexiDEV/ApplicationToolkitPro.git)
    ```
2.  Install the required Python libraries:
    ```sh
    pip install -r requirements.txt
    ```
3.  Run the application:
    ```sh
    python apc.py
    ```

---

## 🛠️ Usage Tips

### Activating the Context Menu Feature

To enable the "Uninstall Program" right-click feature on shortcuts, you must run Application Toolkit Pro as an **administrator**.

1.  Once the application is open with admin rights, navigate to the top menu: `Tools > Context Menu Settings`.
2.  Click on `"Add 'Uninstall Program' Command (.lnk)"`.

This will register the feature in the Windows Registry.

---

## 🤝 Contributing

Contributions are welcome! Please feel free to open an issue or submit a pull request.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).# Application Toolkit Pro

**Author:** KarexiDEV

A comprehensive and powerful application manager for Windows, designed to provide detailed insights and easy management of installed software, including Win32 applications, UWP (Microsoft Store) apps, and portable programs.

---

## ✨ Key Features

* **All-in-One Dashboard:** View all your installed Win32, UWP, and scanned portable applications in a clean, tabbed interface.
* **Smart Categorization:** Automatically sorts programs into 'Applications' and 'Games' for better organization.
* **Advanced Filtering:** Quickly find any application by searching for its name or publisher. Further refine results by installation date, size, architecture (64-bit/32-bit), or installation drive.
* **Detailed Information Panel:** Select any application to see in-depth details like version, publisher, installation date, estimated size, full path, and associated registry key.
* **Powerful Uninstaller:** Uninstall one or multiple programs at once. Includes a **"Try Silent Uninstall"** option to attempt an automated, non-interactive removal.
* **Portable App Scanner:** Scan any folder on your system to find and list portable applications that don't appear in the standard Windows program list.
* **Favorites System:** Mark important applications as favorites for quick access in a dedicated tab.
* **Windows Integration:**
    * **Context Menu:** Add an "Uninstall Program" option to the right-click menu of shortcuts (.lnk files) for quick removal (Requires Admin rights).
    * **System Tray:** The application can be minimized to the system tray to run unobtrusively in the background.

### 💡 About Application/Game Classification

The program distinguishes between the 'Applications' and 'Games' tabs using a local method based on keywords found in application names and publishers. While this method works correctly for most popular software, it may occasionally result in incorrect classifications.

The original version of this project included a more advanced classification system, but it relied on an external server. This dependency was removed to ensure the open-source version is fully self-contained, transparent, and can run offline.

**How You Can Help**
Improving this classification logic is one of the most valuable contributions you can make to the project. You can help by examining the `classify_program` function in `apc.py` to add more keywords, suggest a smarter local classification logic, or by opening an "issue" to share your ideas.

---

## 📦 Installation (For End-Users)

1.  Download the latest `ApplicationToolkitPro-x.x.x.exe` installer from the project's [Releases](https://github.com/KarexiDEV/ApplicationToolkitPro/releases) page.
2.  Follow the on-screen instructions to complete the installation.
3.  That's it! You can now launch the program.

---

## 💻 For Developers (Running from Source)

To run this program from the source code:

1.  Clone this repository:
    ```sh
    git clone [https://github.com/KarexiDEV/ApplicationToolkitPro.git](https://github.com/KarexiDEV/ApplicationToolkitPro.git)
    ```
2.  Install the required Python libraries:
    ```sh
    pip install -r requirements.txt
    ```
3.  Run the application:
    ```sh
    python apc.py
    ```

---

## 🛠️ Usage Tips

### Activating the Context Menu Feature

To enable the "Uninstall Program" right-click feature on shortcuts, you must run Application Toolkit Pro as an **administrator**.

1.  Once the application is open with admin rights, navigate to the top menu: `Tools > Context Menu Settings`.
2.  Click on `"Add 'Uninstall Program' Command (.lnk)"`.

This will register the feature in the Windows Registry.

---

## 🤝 Contributing

Contributions are welcome! Please feel free to open an issue or submit a pull request.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
