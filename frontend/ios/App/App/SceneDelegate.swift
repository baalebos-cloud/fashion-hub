import UIKit
import Capacitor

class SceneDelegate: UIResponder, UIWindowSceneDelegate {
    var window: UIWindow?

    func scene(_ scene: UIScene, willConnectTo session: UISceneSession, options connectionOptions: UIScene.ConnectionOptions) {
        guard let windowScene = scene as? UIWindowScene else { return }

        window = UIWindow(windowScene: windowScene)
        window?.rootViewController = TailoraBridgeViewController()
        window?.makeKeyAndVisible()

        SceneDelegateProxy.shared.scene(scene, willConnectTo: session, options: connectionOptions)
    }

    func scene(_ scene: UIScene, openURLContexts URLContexts: Set<UIOpenURLContext>) {
        SceneDelegateProxy.shared.scene(scene, openURLContexts: URLContexts)
    }

    func scene(_ scene: UIScene, continue userActivity: NSUserActivity) {
        SceneDelegateProxy.shared.scene(scene, continue: userActivity)
    }

    // MASVS-STORAGE / OWASP MASTG: iOS saves a picture of the screen for the app switcher. Cover the
    // app before that happens so a NIN, address, order or chat is never kept in that picture.
    private var privacyCover: UIView?

    func sceneWillResignActive(_ scene: UIScene) {
        guard let window = window, privacyCover == nil else { return }
        let cover = UIView(frame: window.bounds)
        cover.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        cover.backgroundColor = UIColor(red: 0xF6 / 255.0, green: 0xF5 / 255.0, blue: 0xF2 / 255.0, alpha: 1)
        let name = UILabel()
        name.text = "Tailora"
        name.font = UIFont(name: "Georgia", size: 34) ?? .systemFont(ofSize: 34, weight: .semibold)
        name.textColor = UIColor(red: 0x1C / 255.0, green: 0x22 / 255.0, blue: 0x33 / 255.0, alpha: 1)
        name.translatesAutoresizingMaskIntoConstraints = false
        cover.addSubview(name)
        NSLayoutConstraint.activate([
            name.centerXAnchor.constraint(equalTo: cover.centerXAnchor),
            name.centerYAnchor.constraint(equalTo: cover.centerYAnchor),
        ])
        window.addSubview(cover)
        privacyCover = cover
    }

    func sceneDidBecomeActive(_ scene: UIScene) {
        privacyCover?.removeFromSuperview()
        privacyCover = nil
    }
}

/// The web page scrolls under the status bar (the strip with the clock), so a scrolled page showed
/// through above the app's top bar. A solid strip in Tailora's paper colour covers that area.
class TailoraBridgeViewController: CAPBridgeViewController {
    private let statusBarCover = UIView()

    override func viewDidLoad() {
        super.viewDidLoad()
        statusBarCover.backgroundColor = UIColor(red: 0xF6 / 255.0, green: 0xF5 / 255.0, blue: 0xF2 / 255.0, alpha: 1)
        statusBarCover.isUserInteractionEnabled = false
        statusBarCover.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(statusBarCover)
        NSLayoutConstraint.activate([
            statusBarCover.topAnchor.constraint(equalTo: view.topAnchor),
            statusBarCover.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            statusBarCover.trailingAnchor.constraint(equalTo: view.trailingAnchor),
            statusBarCover.bottomAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor),
        ])
    }

    override func viewDidLayoutSubviews() {
        super.viewDidLayoutSubviews()
        view.bringSubviewToFront(statusBarCover)
    }
}
