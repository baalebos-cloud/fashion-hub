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
