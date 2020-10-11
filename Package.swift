// swift-tools-version:5.3
import PackageDescription

let package = Package(
    name: "highlight-kit",
    platforms: [
        .macOS(.v10_15),
    ],
    dependencies: [],
    targets: [
        .target(
            name: "COnig",
            path: "swift/Sources/COnig",
            exclude: [
                "regposerr.c",
                "regposix.c",
                "unicode_egcb_data.c",
                "unicode_property_data.c",
                "unicode_property_data_posix.c",
                "unicode_wb_data.c",
            ],
            publicHeadersPath: "include"
        ),
    ]
)
