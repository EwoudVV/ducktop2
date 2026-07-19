import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    color: "#080a0c"

    Image {
        anchors.fill: parent
        source: config.background
        fillMode: Image.PreserveAspectCrop
        opacity: 0.88
    }

    Rectangle {
        anchors.fill: parent
        color: "#080a0c"
        opacity: 0.28
    }

    Rectangle {
        id: loginFrame
        width: Math.min(parent.width * 0.32, 520)
        height: 260
        anchors.right: parent.right
        anchors.rightMargin: Math.max(parent.width * 0.08, 80)
        anchors.verticalCenter: parent.verticalCenter
        color: "#101418"
        border.color: "#ffb000"
        border.width: 1
        opacity: 0.94

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 28
            spacing: 14

            Text {
                text: "DUCKTOP2"
                color: "#ffb000"
                font.family: "JetBrains Mono"
                font.pixelSize: 26
                font.bold: true
                Layout.fillWidth: true
            }

            Text {
                text: Qt.formatDateTime(new Date(), "yyyy-MM-dd  HH:mm")
                color: "#00d7ff"
                font.family: "JetBrains Mono"
                font.pixelSize: 13
                Layout.fillWidth: true
            }

            ComboBox {
                id: userBox
                model: userModel
                textRole: "name"
                Layout.fillWidth: true
            }

            TextField {
                id: passwordBox
                placeholderText: "password"
                echoMode: TextInput.Password
                Layout.fillWidth: true
                focus: true
                Keys.onReturnPressed: sddm.login(userBox.currentText, passwordBox.text, sessionBox.currentIndex)
                Keys.onEnterPressed: sddm.login(userBox.currentText, passwordBox.text, sessionBox.currentIndex)
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 10

                ComboBox {
                    id: sessionBox
                    model: sessionModel
                    textRole: "name"
                    Layout.fillWidth: true
                }

                Button {
                    text: "login"
                    onClicked: sddm.login(userBox.currentText, passwordBox.text, sessionBox.currentIndex)
                }
            }

            Text {
                text: sddm.hostName
                color: "#8b949b"
                font.family: "JetBrains Mono"
                font.pixelSize: 12
                Layout.fillWidth: true
            }
        }
    }

    Text {
        anchors.left: parent.left
        anchors.leftMargin: 56
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 38
        text: "DUCKTOP2"
        color: "#ffb000"
        font.family: "JetBrains Mono"
        font.pixelSize: 18
        font.bold: true
    }
}
