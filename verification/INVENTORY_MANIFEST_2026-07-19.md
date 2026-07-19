# Ducktop2 Inventory Manifest

Generated UTC: `2026-07-19T21:50:03+00:00`
Root schematic SHA-256: `f2e2678d25c7ef6afdcfe037f0c47fbcd2dbdcf2f40ba5e6954c92de9f0cc110`
Normalized XML netlist SHA-256: `e649d59a1c6be3cc1ee3e94dc55d215dad990ab94c32b896ab5e7802ca19de11`
Recursive source-tree SHA-256: `02ffb87bf1b1e89689c7b52bc4d46f039d9affed655532e458c8d833093232be`
Components: `1004`
Connected pin rows: `3966`
Nets: `1261`

The CSV inventories are valid only when all three embedded hashes match this manifest.
The recursive digest covers the live hierarchy, every generator/checker Python file, all project-local symbol libraries, every footprint in each project-local .pretty library, and both library tables.
Older inventory counts and retired design rows are historical and must not be used for procurement.

## Schematic hierarchy

- `01_power_battery.kicad_sch`: `a5e578fb28c192be4adbb7cf8ad9774e920acdfdccd644bccbd77563ad61d9a1`
- `02_ec_mcu.kicad_sch`: `6edce97968120ceda1a5f0e277fb0ff14bc0b95c569cc573a6812c11f5729a59`
- `03_mu_carrier.kicad_sch`: `c8df735a9f4bf78fcf0d1b4ff9eba279215f9260106ecd0f825ab58ad84fe3a5`
- `04_usb_c_io.kicad_sch`: `d4bd74a4ca84fe20956bb84396059a7c2771ab134d0c3ad5dd6b34e6fe3e466e`
- `05_power_inputs.kicad_sch`: `9588462fa6192d7ffb74db3b4e0d4224835fe3ec846d2d8e0eb1ef83708258f2`
- `06_tcp0_external_hdmi.kicad_sch`: `57bd59556832b09ba042d9b44c742f7acd8e86d04e9393029e1ff09fd23ac39a`
- `07_radio_oled_gps.kicad_sch`: `13fd2d1eb70f7bedbac4f940dffcea5a825a7b89aeb1c7584fddafd5d87ddfc4`
- `08_internal_services.kicad_sch`: `cc90cae54cbf8ef6b909210b185c818982de2ce0b78fd92a95746cda945e252f`
- `09_ham_radio.kicad_sch`: `b8cd7ea4b77b80c3683303320173ec779295e46c86947884e01503ca1a86fb83`
- `12_keyboard_interface.kicad_sch`: `5810900ff6da4215a0682776294197a7ef4a9bad72e26c03210072fbaaf6536d`
- `13_radio_audio_codec.kicad_sch`: `3fe55c6ef4fd5b781066c24900b5ec1d4d8c069f40689d3b5eae1c01e27a97f0`
- `14_maker_mcu.kicad_sch`: `ecbb7f418a4cbacf6322ea7ee92dc25c0279ccd14813090c4a09230e35495623`
- `15_system_audio.kicad_sch`: `f1a43f4e24e95d9966d7753de064f4983f6d0857a85467f4f345821ef5f06be9`
- `16_gigabit_ethernet.kicad_sch`: `4883d9a9b0c713421a69854f5c43dc194b0af9d728688543c955e39f342d88e1`
- `ducktop2.kicad_sch`: `f2e2678d25c7ef6afdcfe037f0c47fbcd2dbdcf2f40ba5e6954c92de9f0cc110`

## Generator and checker Python

- `gen/apply_mechanical_retention_eco.py`: `06fb2abc4971c8ab94bf9abceeea6c49d01ab2ef983bf8b1393b361e457893ca`
- `gen/apply_mu_standoff_release_eco.py`: `b97a1756be76f482c23f5e0d75cfdc1d0fb0005373f6638e823b340bc7887d9a`
- `gen/build_ducktop2.py`: `677935280713ae276780e088808adc779e0cc9bfa36ae693226b702847816734`
- `gen/check_release_candidate.py`: `c1ac54fb459842fc1a8887d455b865087d1113b88e78a9ce77b0e94076e269ad`
- `gen/check_schematic.py`: `48b3983f6c7bdd2ec46370c432f1853cdd2b1643701ea98797f4f483ab32111a`
- `gen/clear_main_pcb_routing.py`: `9b813d8c0fc9fefb7bf0463ca7f213b7d4d247ecb7db2e44cb3a2a6d56a9bb54`
- `gen/generate_component_inventory.py`: `3655e5d84091f2a33e8ca7f29f38a5624d6d31a94bdd9be84cdbb8b62cbb8c35`
- `gen/generate_ec_mcu_sheet.py`: `28d26c0cfb6956394f93635c6b0747c93aaf1314ffee746fb0f6415d1d3a501c`
- `gen/generate_ethernet_sheet.py`: `73ebfad313ee850d7c0d181519792c22a884faad8903693fb6192c0bf5bc24ee`
- `gen/generate_ham_radio_sheet.py`: `70f25d4b48674b8bf51b8950687b83bac72c38fadf869e88e57276ca8967ad8d`
- `gen/generate_internal_services_sheet.py`: `a478e761f2496906b3e9fd91d48f747a3bf062117e6062579e0ea2ca3811005a`
- `gen/generate_keyboard_daughterboard_pcb.py`: `0185f5fe19e9869d4ee9deeef6816114f9a6bd5ae7809ea4dd4aa7bcffd27339`
- `gen/generate_keyboard_daughterboard_sheet.py`: `390c29bd243b1f0645d8b0e0ea5f337ab821adbe39ca79fc29d2a047076b1cb2`
- `gen/generate_keyboard_interface_sheet.py`: `fcdf8e2365eeac13269b35d90f184e8f4644e2b0374fce7483b0aaf584d9d8a0`
- `gen/generate_keyboard_jlcpcb_package.py`: `357a8cf15a16f4beec741c5497aca8dbad01be3c6c907e5022e26355d603525d`
- `gen/generate_main_pcb_mechanical_envelope.py`: `766d3dddcc759984c6f7a87bba367a5e3f237c1d23a857c5326085e18ada3354`
- `gen/generate_maker_mcu_sheet.py`: `1022aaee61160a003ea68a367cac92344c731159955bdc4335fef7ed915a3940`
- `gen/generate_mu_carrier_sheet.py`: `07f71706bbe5e026d980ee8c1a39e92c02620cb2c7e840e05250240364cf3339`
- `gen/generate_pin_review_table.py`: `692cad182c1bac52ed1f938ab792f3f3329f8e3812243a26b08e1d115998784a`
- `gen/generate_power_inputs_sheet.py`: `e92f3ceb906e0e394e10989d1be14a22a03126211a03baeb3b3a6242a83d87a9`
- `gen/generate_power_sheet.py`: `a936137a5bf3cd0a7917f6b3ce26b8b07ffe3ef315dcc61c64c7f42c3b5eab4d`
- `gen/generate_radio_audio_codec_sheet.py`: `ac9e0ba0e68fb4b9154d184e450f976f276821b7b2cfff8f53d8fb5b1e96618f`
- `gen/generate_radio_oled_gps_sheet.py`: `438194594a023a3b8d04b7c385af1c75739fa67a1c03db9bbeaf12f33acf2f5c`
- `gen/generate_system_audio_sheet.py`: `c4940b2c130e77747b939e13a1d8b869d425b0e86e8764b0545b2241b5f5fbd2`
- `gen/generate_tcp0_external_hdmi_sheet.py`: `55bb2b1549570807dca9170566d7013a804a53afd54de16ae55e4412f1a6e40c`
- `gen/generate_usb_c_io_sheet.py`: `98049a46e2e4b8ba5306f56e8cb8a3b0390f68c5efca13698cc9cfcfb5f2f1a9`
- `gen/genlib.py`: `c4ae7256e7187ae374ebc57764d98b59689d0a0e928bb7c76a3eb697d32ee15a`
- `gen/place_post_audit_eco_footprints.py`: `56e89dcfc75674c0585328f506d59b179b685b5fadfd726842f01c0d0851c223`
- `gen/place_remaining_offboard_footprints.py`: `ef32af7b6767e4e09cba025850c47baf870e77e6b7eebe2de40bb408ed658ea1`
- `gen/prepare_main_pcb_layout.py`: `d2942399749f7d5795432ae99e4736caf960906930d149fa7c9afac64a38b4f6`
- `gen/rebuild_main_pcb_revC.py`: `7d56e7bca54a2825f434fa4d2346c2530f49f6fc73454fa2d7ca85e56393b1bc`
- `gen/report_schematic_pcb_eco.py`: `7fb2f7bbc757d864ada47b568cbaebafb3beb87631f0e0e08a044b09fb4d3435`
- `gen/sync_main_pcb_from_netlist.py`: `0513ac76d41a1cf843958c145c8eb24dca37bdb56293a61be3085b14b7775cec`
- `gen/verify_design_contracts.py`: `0f26dc91eb7835d92410adbed89816795201d324b7b16370665db9467e5bf101`
- `gen/verify_electrical_calculations.py`: `f5dfd26743204eb5706147f85f7e7530dcb6e084908201ba3fe7f47c956a7759`
- `gen/verify_pcb_eco_candidate.py`: `4ff6ea79da3ef0505b2ea5d41a59c181cda9750bca66c8fb4121b60608d19038`
- `gen/verify_schematic_closure.py`: `ae661ffc69b9c18e7b3568d97cd09a3e9dec28ee9bf6018b63f59e884139fb42`

## Project-local symbol libraries

- `gen/AMS1117-3.3.kicad_sym`: `ab2c7c13c9685f411d6a885e4d10f3531fd483adc72d71fdead6ac452b490452`
- `gen/AP2112K-3.3.kicad_sym`: `13d2df64aa7b19d0230bee1c9eda9e3c68b58fd9047e12ce01f4ce8f1887c643`
- `gen/BQ24650.kicad_sym`: `13281176b50e279f2671475871bb9f8e9b5cdbbbda38a79405c5188fe490411d`
- `gen/BQ25798.kicad_sym`: `0b49501edcec74690d12d21cee414b69c35655ae133f447ba67ea9a474e13aeb`
- `gen/BQ34Z100-G1.kicad_sym`: `baec8bfa845f5ac24fef8db98995de2907ab4dcb69f5189f19baa48bd05f519d`
- `gen/BQ76920PW.kicad_sym`: `2d545254654238b49d1526edf51b426fb8c980a5cf1c666316b85599e0eb9555`
- `gen/BQ77915.kicad_sym`: `fe24133b0842fc118f2421b91f9a19ec6ff493fb0ee60b3cb42a7294848700c9`
- `gen/Battery_Cell.kicad_sym`: `73a1110ac2ec61e4422a71ee57795305eb748b3c11797d914baf8c6d39923620`
- `gen/Bus_M.2_Socket_E.kicad_sym`: `7f1d10cf7d08ac3aa2480753fd0be5f6bad2bf312b015d1fa8c6ddc316abd24d`
- `gen/Bus_M.2_Socket_M.kicad_sym`: `e97b30fdfa4e830d2103cea285812a1873f0a4b7f8ab4e80f6beb985c9bba660`
- `gen/C.kicad_sym`: `533df5a016c224a83701e2e66b767864f39fc44c972a2a4f821987f1fd99573e`
- `gen/CH224A.kicad_sym`: `cc3fa5c411467215fa0569be08425ec9fff97704e77c84bc582813498e5e63d9`
- `gen/C_Polarized.kicad_sym`: `e0371fff515df9a22bc5e6d82a2164943da1d389e2ccf0d220ff03d7d77cc87a`
- `gen/Cherry_MX_ULP.kicad_sym`: `ce6bd75cf4faf6257df643f98ce2b61325ecc8799250e0fbe9cc3cc983a37345`
- `gen/Conn_01x02.kicad_sym`: `0fa71012f16ff9329d578174b763d6aee9b64f3b5112db4416a0cf5df7491fdc`
- `gen/Conn_01x04.kicad_sym`: `6047a81578c35a3eb39e5bb055d85acb20523327c75cf327fa436cb33acbd69b`
- `gen/Conn_01x06.kicad_sym`: `985cba4c01de2dbec9e7bad0ddf1e16d613f21fa29d407fbe84cc019c76b29ee`
- `gen/Conn_01x08.kicad_sym`: `f03d1fab0abf160fb6132e2a86bfb15d0dc9b66c7a3b0e8aed38f462486f9a40`
- `gen/Conn_01x10_FFC_MP.kicad_sym`: `9547e0e275f62ebebc3d5e258b8b3c0c151bd1b75d121fb49478614475d3edb1`
- `gen/Conn_01x16.kicad_sym`: `532ade76ad9a6a9eb8406d30c5f3077ee249280a59d0d9d969933fa170089b77`
- `gen/Conn_01x30_FFC_MP.kicad_sym`: `860ce05ee1a3ff4724deefc3832eb60fe42fd8d1c33a5792f2788d6e0743cbe0`
- `gen/Connector_Generic.kicad_sym`: `388a17a5dfb3d6f1ac7e6e4bb79dfe4ea3cdbbc4ade8f374e3f16a4a530340ed`
- `gen/Crystal.kicad_sym`: `d9f44c34d11880200f0ff89878d46de4df003191e34aab325d22aee75b8691da`
- `gen/DRA818.kicad_sym`: `c2b6c2a69d4b6fbf0acf3051a30df57d23b6af149546fa3b7ab2d1368e0b2c10`
- `gen/D_Schottky.kicad_sym`: `4618d1d395991ad2eecf6d39b27d42b447347fb69aeafcb02d741552bb5dc70f`
- `gen/D_Zener.kicad_sym`: `138a686e82ce947e4209933f52e036ed5613027e4b8d3d02c685990ec0fd59fe`
- `gen/Device.kicad_sym`: `b5529115ed63750e656ba669a8b424e133fc7a7255f5dc5535819efba5da3570`
- `gen/Fuse.kicad_sym`: `08d01d9946b9d571c9860b3ca3151a6b36d39516d4b9ec9edc3820046c75dfd2`
- `gen/GND.kicad_sym`: `2505811766064acf321cd3aae4e72ef96d35da64c1ed4ca8d6a24271c9cf7734`
- `gen/IM68A130V01.kicad_sym`: `ab136a05175050868d89b34a14dff8d51cae44e3144493d526899a250a9ebeee`
- `gen/JXD1-1022NL.kicad_sym`: `04a99d5c17e9425413c26d88935b4883e755d79226bd38615cf2789c1793b830`
- `gen/L.kicad_sym`: `ea666fa611b3d896b47a0d12a8f2975511f696384535d3cc85bd039fb9259042`
- `gen/LED.kicad_sym`: `e85b6faf1f41fab98385fbaf44f9cbb87ca7f79c4948d6dba92c73a733db5982`
- `gen/LTC4368-1.kicad_sym`: `2184fe02aca59d5e701c4fec60fa9137f1625c62b5d0ffe40bfd98c9a06e536b`
- `gen/LTC4418IUF.kicad_sym`: `0cf03d7a92e52fb1b3f2a35c99ef28ec4febd83c8c44a96515d16b5d2069f1cc`
- `gen/LattePanda_Mu.kicad_sym`: `4e9834ca97a7824dc733c87c05fa206bbfaa71a5d3bd7d73a516d388581a114c`
- `gen/MiniCircuits_ULP.kicad_sym`: `cdf9d049d460070d5bea395ca64d7b661d1e4ee83d56f40d6c5f982fabdbc7a8`
- `gen/PCA9306DCTR.kicad_sym`: `73bf523e8c21974adb775451cb0dd361ec2a3304746726bd5e1685eb969e56e5`
- `gen/PCM2704C.kicad_sym`: `4d8966731d846af48db78ced66e4b0afeb01932c8638d4be5b63d1598eef33fb`
- `gen/PCM2900C.kicad_sym`: `208727b42c09b4b45af850c264b880d13c0295b725d985a39e3eecc2461c1d92`
- `gen/PE42820.kicad_sym`: `fb8718ae0f3c53a92baf5cf89a3d4b16c912f9252b8650c1de9ef5171f063c75`
- `gen/PWR_FLAG.kicad_sym`: `5308c8c77530d5ba458ca658925119069cb6cb8ad6fbf424d88afb1fdb4e3ef1`
- `gen/Q_NMOS.kicad_sym`: `d8323b08af0db79775b9ab3aad95d8ddd8291c79d125cc9cab705cec0268ccfd`
- `gen/Q_NMOS_123S_4G_5678D.kicad_sym`: `b35caa90175e97fe7c6edd62f1f48d04541babd80aa7dbfb3012b2c1f8ec5823`
- `gen/Q_NMOS_SOT23_GSD.kicad_sym`: `ecce10e0f66a3c2b53a472e3204c7671b83946aad58e1f12a877fe8f24a0e4db`
- `gen/Q_NMOS_TO252_GDS.kicad_sym`: `1189a85bc64045b342819a21207163f7c196573393c482dc5a3826e0d402949f`
- `gen/Q_PMOS_1G_234S_5D.kicad_sym`: `fed42f1fb588a96654922f766a9d6546e090391e24b8bb4f31c7d708be2d7386`
- `gen/R.kicad_sym`: `db1dd3eb60dbcc9e239d107e2d123ee253aefdd841186076e9df39444d4e11c7`
- `gen/RT6150BGQW.kicad_sym`: `8c25e00e2e033727b6934f261b96d0aeeec4cf068e7cd4ad95eba1fb23953289`
- `gen/RTL8111H.kicad_sym`: `2876bae4bf75d016f567d9fd27a7a9e4e5fb1c88a2ba29fd4f7a7b62c54fcf5b`
- `gen/R_Small.kicad_sym`: `1a9e8dc00f070690bbd2af751703e994e72bc135eb2e9d163f4d5ed5ca384a30`
- `gen/SN74CB3T3245.kicad_sym`: `072edee4322cad345bb7903118c0e9c37fec62f5161f473baa08139fbdd8bd48`
- `gen/STM32F407VGTx.kicad_sym`: `ffafad115d5893c7ada8c8f555ae4c4809a4847a7ca68a05f191c440012bafd8`
- `gen/SW_Push.kicad_sym`: `2e457acb01b087375c8481af6ca3843a4cce42e7acdb7b2b4400058fcdc4d0c0`
- `gen/SY8253ADC.kicad_sym`: `59a84d36cf5917b170042ad39dab78acdf2a0851ef0c26041c840a8d40b63aa9`
- `gen/TLV803EA29RDBZR.kicad_sym`: `7a18d4f12c17199a9de1bf012263c0c8b48deb486537eb4ee8c569ec454f6643`
- `gen/TLV803EA43RDBZR.kicad_sym`: `4994cd829962122bdbd71aae62c0764d19c77eec2311172dc43c02eb395d7d51`
- `gen/TPA2012D2.kicad_sym`: `9e5b88f2a974cc78e8651f081fdf42f65e44299a190877be10d02217491eb1b4`
- `gen/TPD13S523PWR.kicad_sym`: `c240928ee04c22022fb17342e845491ca736c295bac3468b91787fb5b6c58a15`
- `gen/TPS2052B.kicad_sym`: `72ae1125d40554dd54c144dfa8fa4d994296581f452899ac4d8ebef60262733a`
- `gen/TPS22975N.kicad_sym`: `2315a9e7235db1d90758ef6c5e88e658c1950bdc089ba837cecb930504be2920`
- `gen/TPS2553D.kicad_sym`: `be7321a90e878d5167076068930a19c43b5df5a4219b2306d720e5440d73ee8f`
- `gen/TPS259470A.kicad_sym`: `780e3d81e55a86a6719b927640369b68808ceee9116529bebbb30be546fe475d`
- `gen/TPS54202DDC.kicad_sym`: `acfb18466c6fde5937948b520135fe243e6929ef34c48d17f98e056728b67b3c`
- `gen/TPS54302.kicad_sym`: `771adef352b5316f99189614ebcd58498171b0bba838bd1f33ff018aa98a6e61`
- `gen/TPS552892.kicad_sym`: `5e1c51c6463e5bdf08070225985b22a1cb83cd36880c40f8fc1c231f432fb396`
- `gen/TPS56637.kicad_sym`: `cb05c838d664f37e3889b0ba909f1c9c9337f4b349bad4cfe8f86fb1c13ba600`
- `gen/TPS62821DLC.kicad_sym`: `7db90bec6f77e2404071a6361b440b57a82380573ec48cec0bb59e5cd1294186`
- `gen/TPS7A0210.kicad_sym`: `8b2b35fee6b90a2e7fbdc7dd3c3025e9ce65687914ef8abd39d4127a8c270253`
- `gen/TUSB8020BIPHP.kicad_sym`: `8a55f6436f59e6876569810fed487cd200b4d9a48218c351744c513d8d7a4007`
- `gen/Thermistor_NTC.kicad_sym`: `df87ca99d452d3dcdc56a163ff3ba4209369b8814206730c36e27da10e782f4f`
- `gen/USB2512B.kicad_sym`: `cb753c932777cc60b5b14f73435b11fe7d64f49af7105fe73d38b2ac69e87523`
- `gen/USB3_A.kicad_sym`: `c1743246eee3167799c577bcd33042cf145a2f46addf8504aefe714b21a15a2d`
- `gen/USB_C_Receptacle_Passive.kicad_sym`: `3250544059873e026a0dd3c20fc363dbda17ad81c878601e2484ce513b206622`
- `gen/VL822-Q7.kicad_sym`: `8ffa49116fc5789ea2c4880e8b0a7d75fb00aa38612625893fad631d356d2a1d`
- `gen/ducktop2.kicad_sym`: `a3a677d2c27215363eda1222635ac0c1e3dcf9e64976d7e2670c8890e544d049`
- `gen/power.kicad_sym`: `409229e4de9e65a9a4560812bf0656da6d5e22bfc50ff69d7267119bb779afdd`

## Project-local footprint libraries

- `Module_LattePanda.pretty/LattePanda_Module_H8.0mm_Horizontal.kicad_mod`: `c9cc2d52a03431e9b8e7ff25d4a7f8a8bfc6839367c8ac7a4939c93ae2551c21`
- `ducktop2.pretty/ADI_UF20_QFN20_4x4_P0.5_EP2.45.kicad_mod`: `41144e8a6239203b04d740bf7e38a950075d1a0791b031ef77c9924f3b5cf2a1`
- `ducktop2.pretty/Amphenol_MDT420E01001_H4.2.kicad_mod`: `e1b14a2be5165e6a7b7fc3b87948b6f5fbeab476653debe9263d3fb691d5935f`
- `ducktop2.pretty/Amphenol_MDT420M01001_H4.2.kicad_mod`: `daf6f07dbeadb910edd12440d6a4a517896303573eaf173aea7cfb113fd0813a`
- `ducktop2.pretty/CSD18540Q5B_DNK.kicad_mod`: `6abc61f6f0fec0b2d59101dda2f28d5bce8f8b804f39b8f1c03904f339114f90`
- `ducktop2.pretty/CSD19537Q3_DQG.kicad_mod`: `ba69faabdf8a5f81f26a36ba7c7963541a77483b1ba0e6b8b85c4d26bde27bda`
- `ducktop2.pretty/Cherry_MX_ULP_SMD.kicad_mod`: `1d8ba042df3bd143fa9b89ad318c8d139dcf14662afac699436ddeea2f1984ab`
- `ducktop2.pretty/Coilcraft_XGL4020.kicad_mod`: `ffb652800c1220b3a926144e67d8929e2e57a6237304fc89b9eccf36b2acf782`
- `ducktop2.pretty/Coilcraft_XGL5030.kicad_mod`: `d2047c7c77f5a383df00eb2b9927943fca830a379a726aaf66020cf0c798cb6e`
- `ducktop2.pretty/Coilcraft_XGL6030.kicad_mod`: `6a709172c4966857cfef4242fdd36eb440efe42cef175171d7ac7016e281ee94`
- `ducktop2.pretty/DRA818_Castellated.kicad_mod`: `dcb4ee7d0ad53f99d7e060324f13d779cf2d73e2e82bbdc54aa696376cc398bd`
- `ducktop2.pretty/Infineon_IM68A130V01.kicad_mod`: `b8df2faf6d01362f5048e1cd49b884d155aa7a80e6dcf722b04ea05c7e45d96d`
- `ducktop2.pretty/JXD1-1022NL_MidMount.kicad_mod`: `9199696c9615cf2c996aa6b21a924cbc56cd13d3781f034d0c5dffb76fe446f5`
- `ducktop2.pretty/MiniCircuits_QA2224_PL484.kicad_mod`: `59926b33068a07fe74c57ed34b4e37a865b7ff56a6b9512838cf219d37636eb3`
- `ducktop2.pretty/PE42820_QFN-32-1EP_5x5mm_P0.5mm.kicad_mod`: `4071fc391c6814aa08a50d3ef18a7a040c32b6946351f06bfe4a5c9791566647`
- `ducktop2.pretty/QFN-76-1EP_9x9mm_P0.4mm_EP6.3x6.3mm.kicad_mod`: `89d181abf51bc5a8aa40e513fb95406250da85147bfa13603962abd0a8d6a02c`
- `ducktop2.pretty/SMT_Standoff_M2_H2.5_C4_Tail2.7x1.5.kicad_mod`: `41944f1e46f5f8dede7ff5e0e0cac021085eec703053e56afd864e6aea5d652f`
- `ducktop2.pretty/SMT_Standoff_M2_H5.5_C4_Tail3.0x1.5.kicad_mod`: `a626383cd5f8991d5df9560dcc457a6f60f834008c4567f728d967e91cd8b71a`
- `ducktop2.pretty/SSD1306_0.96in_Module_4Pin.kicad_mod`: `bc0d1086cef3a188f2e7d8bf2879c7945b089ab66bd1782fd33b67885f04ab32`
- `ducktop2.pretty/TDK_TFM201610.kicad_mod`: `d02bb7cb6700abc12952439173c4e8d0a8a0f45543b6e844905651becccd5a6d`
- `ducktop2.pretty/Texas_RPA0010A_VQFN-HR-10_3x3mm.kicad_mod`: `fed7ac067f735241c4fa93fbcc90e21c416334e4e84e58dc0c694db7f39963fb`
- `ducktop2.pretty/Texas_RPW0010A_VQFN-HR-10_2x2mm.kicad_mod`: `8a7852254f29dd4b30d3569f2e496265f3472754cc3df1632c255121a7d6cda5`
- `ducktop2.pretty/Texas_RYQ0021A_VQFN-HR-21_3x5mm.kicad_mod`: `65f155f68df66646efa0b4654aa54b48aede168f60f82b64c165a105da7e27bd`
- `ducktop2.pretty/Wurth_9774055243R_M2_H5.5.kicad_mod`: `d79738a05736ecff95bb56475dbd4d699da442af71179f0b0048b69417008bd6`
- `ducktop2.pretty/X2SON-4_1.0x1.0mm_P0.65mm.kicad_mod`: `cd48bfb1b483ce367f1cd7714d096a320dd879dccbf30dd3c6580480af55581c`

## KiCad project library tables

- `sym-lib-table`: `5758fb2a4dc0857a0c9b5570e45492371f43b6ad4a9a050f4928260884bacfc3`
- `fp-lib-table`: `0f421214663f50ea18cf9e593d701239c4d6f163f03cb82ebe28bbdac1846769`

## Active ducktop2 Footprints in the Netlist

These active-source hashes are a convenience subset; the project-local footprint section above is authoritative and complete.

- `ADI_UF20_QFN20_4x4_P0.5_EP2.45`: `41144e8a6239203b04d740bf7e38a950075d1a0791b031ef77c9924f3b5cf2a1` (25 pad records)
- `Amphenol_MDT420E01001_H4.2`: `e1b14a2be5165e6a7b7fc3b87948b6f5fbeab476653debe9263d3fb691d5935f` (71 pad records)
- `Amphenol_MDT420M01001_H4.2`: `daf6f07dbeadb910edd12440d6a4a517896303573eaf173aea7cfb113fd0813a` (71 pad records)
- `CSD18540Q5B_DNK`: `6abc61f6f0fec0b2d59101dda2f28d5bce8f8b804f39b8f1c03904f339114f90` (17 pad records)
- `CSD19537Q3_DQG`: `ba69faabdf8a5f81f26a36ba7c7963541a77483b1ba0e6b8b85c4d26bde27bda` (13 pad records)
- `Coilcraft_XGL5030`: `d2047c7c77f5a383df00eb2b9927943fca830a379a726aaf66020cf0c798cb6e` (2 pad records)
- `DRA818_Castellated`: `dcb4ee7d0ad53f99d7e060324f13d779cf2d73e2e82bbdc54aa696376cc398bd` (18 pad records)
- `Infineon_IM68A130V01`: `b8df2faf6d01362f5048e1cd49b884d155aa7a80e6dcf722b04ea05c7e45d96d` (11 pad records)
- `JXD1-1022NL_MidMount`: `9199696c9615cf2c996aa6b21a924cbc56cd13d3781f034d0c5dffb76fe446f5` (20 pad records)
- `MiniCircuits_QA2224_PL484`: `59926b33068a07fe74c57ed34b4e37a865b7ff56a6b9512838cf219d37636eb3` (6 pad records)
- `PE42820_QFN-32-1EP_5x5mm_P0.5mm`: `4071fc391c6814aa08a50d3ef18a7a040c32b6946351f06bfe4a5c9791566647` (52 pad records)
- `SMT_Standoff_M2_H2.5_C4_Tail2.7x1.5`: `41944f1e46f5f8dede7ff5e0e0cac021085eec703053e56afd864e6aea5d652f` (2 pad records)
- `SSD1306_0.96in_Module_4Pin`: `bc0d1086cef3a188f2e7d8bf2879c7945b089ab66bd1782fd33b67885f04ab32` (4 pad records)
- `TDK_TFM201610`: `d02bb7cb6700abc12952439173c4e8d0a8a0f45543b6e844905651becccd5a6d` (2 pad records)
- `Texas_RPA0010A_VQFN-HR-10_3x3mm`: `fed7ac067f735241c4fa93fbcc90e21c416334e4e84e58dc0c694db7f39963fb` (19 pad records)
- `Texas_RPW0010A_VQFN-HR-10_2x2mm`: `8a7852254f29dd4b30d3569f2e496265f3472754cc3df1632c255121a7d6cda5` (10 pad records)
- `Texas_RYQ0021A_VQFN-HR-21_3x5mm`: `65f155f68df66646efa0b4654aa54b48aede168f60f82b64c165a105da7e27bd` (36 pad records)
- `Wurth_9774055243R_M2_H5.5`: `d79738a05736ecff95bb56475dbd4d699da442af71179f0b0048b69417008bd6` (2 pad records)
