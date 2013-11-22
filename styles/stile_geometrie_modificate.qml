<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis version="1.7.0-Wroclaw" minimumScale="0" maximumScale="1e+08" hasScaleBasedVisibilityFlag="0">
  <transparencyLevelInt>255</transparencyLevelInt>
  <renderer-v2 type="RuleRenderer">
    <rules>
      <rule scalemaxdenom="10000000" description="" filter="ABBINATO_A_SCHEDA = '1'" symbol="0" scalemindenom="25000" label="1:25k - oltre : con scheda"/>
      <rule scalemaxdenom="10000000" description="" filter="ABBINATO_A_SCHEDA = '0'" symbol="1" scalemindenom="25000" label="1:25k - oltre : senza scheda"/>
      <rule scalemaxdenom="25000" description="" filter="ABBINATO_A_SCHEDA = '1' AND ZZ_STATO_GEOMETRIAID = '1'" symbol="2" scalemindenom="2000" label="1:2k - 1:25k : invariate con scheda"/>
      <rule scalemaxdenom="25000" description="" filter="ABBINATO_A_SCHEDA = '1' AND ZZ_STATO_GEOMETRIAID = '2'" symbol="3" scalemindenom="2000" label="1:2k - 1:25k : modif. con scheda"/>
      <rule scalemaxdenom="25000" description="" filter="ABBINATO_A_SCHEDA = '1' AND ZZ_STATO_GEOMETRIAID = '9'" symbol="4" scalemindenom="2000" label="1:2k - 1:25k : nuove con scheda"/>
      <rule scalemaxdenom="25000" description="" filter="ABBINATO_A_SCHEDA = '0' AND ZZ_STATO_GEOMETRIAID = '1'" symbol="5" scalemindenom="2000" label="1:2k - 1:25k : invariate senza scheda"/>
      <rule scalemaxdenom="25000" description="" filter="ABBINATO_A_SCHEDA = '0' AND ZZ_STATO_GEOMETRIAID = '2'" symbol="6" scalemindenom="2000" label="1:2k - 1:25k : modif. senza scheda"/>
      <rule scalemaxdenom="25000" description="" filter="ABBINATO_A_SCHEDA = '0' AND ZZ_STATO_GEOMETRIAID = '9'" symbol="7" scalemindenom="2000" label="1:2k - 1:25k : nuove senza scheda"/>
      <rule scalemaxdenom="2000" description="" filter="ABBINATO_A_SCHEDA = '1' AND ZZ_STATO_GEOMETRIAID = '1'" symbol="8" scalemindenom="1" label="1:1 - 1:2k : invariate con scheda"/>
      <rule scalemaxdenom="2000" description="" filter="ABBINATO_A_SCHEDA = '1' AND ZZ_STATO_GEOMETRIAID = '2'" symbol="9" scalemindenom="1" label="1:1 - 1:2k : modif. con scheda"/>
      <rule scalemaxdenom="2000" description="" filter="ABBINATO_A_SCHEDA = '1' AND ZZ_STATO_GEOMETRIAID = '9'" symbol="10" scalemindenom="1" label="1:1 - 1:2k - nuove con scheda"/>
      <rule scalemaxdenom="2000" description="" filter="ABBINATO_A_SCHEDA = '0' AND ZZ_STATO_GEOMETRIAID = '1'" symbol="11" scalemindenom="1" label="1:1 - 1:2k : invariate senza scheda"/>
      <rule scalemaxdenom="2000" description="" filter="ABBINATO_A_SCHEDA = '0' AND ZZ_STATO_GEOMETRIAID = '2'" symbol="12" scalemindenom="1" label="1:1 - 1:2k : modif. senza scheda"/>
      <rule scalemaxdenom="2000" description="" filter="ABBINATO_A_SCHEDA = '0' AND ZZ_STATO_GEOMETRIAID = '9'" symbol="13" scalemindenom="1" label="1:1 - 1:2k : nuove senza scheda"/>
    </rules>
    <symbols>
      <symbol outputUnit="MM" alpha="1" type="fill" name="0">
        <layer pass="0" class="CentroidFill" locked="0"/>
      </symbol>
      <symbol outputUnit="MM" alpha="1" type="fill" name="1">
        <layer pass="0" class="CentroidFill" locked="0"/>
      </symbol>
      <symbol outputUnit="MM" alpha="0.4" type="fill" name="10">
        <layer pass="0" class="SimpleFill" locked="0">
          <prop k="color" v="170,85,0,102"/>
          <prop k="color_border" v="134,0,0,102"/>
          <prop k="offset" v="0,0"/>
          <prop k="style" v="solid"/>
          <prop k="style_border" v="solid"/>
          <prop k="width_border" v="0.52"/>
        </layer>
        <layer pass="0" class="MarkerLine" locked="0">
          <prop k="interval" v="3"/>
          <prop k="offset" v="0"/>
          <prop k="placement" v="vertex"/>
          <prop k="rotate" v="1"/>
        </layer>
      </symbol>
      <symbol outputUnit="MM" alpha="0.4980392156862745" type="fill" name="11">
        <layer pass="0" class="SimpleFill" locked="0">
          <prop k="color" v="85,170,0,127"/>
          <prop k="color_border" v="0,170,0,127"/>
          <prop k="offset" v="0,0"/>
          <prop k="style" v="diagonal_x"/>
          <prop k="style_border" v="solid"/>
          <prop k="width_border" v="0.26"/>
        </layer>
        <layer pass="0" class="MarkerLine" locked="0">
          <prop k="interval" v="3"/>
          <prop k="offset" v="0"/>
          <prop k="placement" v="vertex"/>
          <prop k="rotate" v="1"/>
        </layer>
      </symbol>
      <symbol outputUnit="MM" alpha="0.4980392156862745" type="fill" name="12">
        <layer pass="0" class="SimpleFill" locked="0">
          <prop k="color" v="170,85,255,127"/>
          <prop k="color_border" v="123,61,184,127"/>
          <prop k="offset" v="0,0"/>
          <prop k="style" v="diagonal_x"/>
          <prop k="style_border" v="solid"/>
          <prop k="width_border" v="0.26"/>
        </layer>
        <layer pass="0" class="MarkerLine" locked="0">
          <prop k="interval" v="3"/>
          <prop k="offset" v="0"/>
          <prop k="placement" v="vertex"/>
          <prop k="rotate" v="1"/>
        </layer>
      </symbol>
      <symbol outputUnit="MM" alpha="0.4980392156862745" type="fill" name="13">
        <layer pass="0" class="SimpleFill" locked="0">
          <prop k="color" v="170,85,0,127"/>
          <prop k="color_border" v="134,0,0,127"/>
          <prop k="offset" v="0,0"/>
          <prop k="style" v="diagonal_x"/>
          <prop k="style_border" v="solid"/>
          <prop k="width_border" v="0.52"/>
        </layer>
        <layer pass="0" class="MarkerLine" locked="0">
          <prop k="interval" v="3"/>
          <prop k="offset" v="0"/>
          <prop k="placement" v="vertex"/>
          <prop k="rotate" v="1"/>
        </layer>
      </symbol>
      <symbol outputUnit="MM" alpha="1" type="fill" name="2">
        <layer pass="0" class="SimpleFill" locked="0">
          <prop k="color" v="85,170,0,255"/>
          <prop k="color_border" v="0,170,0,255"/>
          <prop k="offset" v="0,0"/>
          <prop k="style" v="solid"/>
          <prop k="style_border" v="solid"/>
          <prop k="width_border" v="0.4"/>
        </layer>
      </symbol>
      <symbol outputUnit="MM" alpha="1" type="fill" name="3">
        <layer pass="0" class="SimpleFill" locked="0">
          <prop k="color" v="170,85,255,255"/>
          <prop k="color_border" v="123,61,184,255"/>
          <prop k="offset" v="0,0"/>
          <prop k="style" v="solid"/>
          <prop k="style_border" v="solid"/>
          <prop k="width_border" v="0.4"/>
        </layer>
      </symbol>
      <symbol outputUnit="MM" alpha="1" type="fill" name="4">
        <layer pass="0" class="SimpleFill" locked="0">
          <prop k="color" v="170,85,0,255"/>
          <prop k="color_border" v="134,0,0,255"/>
          <prop k="offset" v="0,0"/>
          <prop k="style" v="solid"/>
          <prop k="style_border" v="solid"/>
          <prop k="width_border" v="0.4"/>
        </layer>
      </symbol>
      <symbol outputUnit="MM" alpha="0.4941176470588236" type="fill" name="5">
        <layer pass="0" class="SimpleFill" locked="0">
          <prop k="color" v="85,170,0,126"/>
          <prop k="color_border" v="0,170,0,126"/>
          <prop k="offset" v="0,0"/>
          <prop k="style" v="diagonal_x"/>
          <prop k="style_border" v="solid"/>
          <prop k="width_border" v="0.4"/>
        </layer>
      </symbol>
      <symbol outputUnit="MM" alpha="0.4941176470588236" type="fill" name="6">
        <layer pass="0" class="SimpleFill" locked="0">
          <prop k="color" v="123,61,184,126"/>
          <prop k="color_border" v="0,0,0,126"/>
          <prop k="offset" v="0,0"/>
          <prop k="style" v="diagonal_x"/>
          <prop k="style_border" v="solid"/>
          <prop k="width_border" v="0.26"/>
        </layer>
      </symbol>
      <symbol outputUnit="MM" alpha="0.4941176470588236" type="fill" name="7">
        <layer pass="0" class="SimpleFill" locked="0">
          <prop k="color" v="170,85,0,126"/>
          <prop k="color_border" v="134,0,0,126"/>
          <prop k="offset" v="0,0"/>
          <prop k="style" v="diagonal_x"/>
          <prop k="style_border" v="solid"/>
          <prop k="width_border" v="0.26"/>
        </layer>
      </symbol>
      <symbol outputUnit="MM" alpha="0.3921568627450981" type="fill" name="8">
        <layer pass="0" class="SimpleFill" locked="0">
          <prop k="color" v="85,170,0,100"/>
          <prop k="color_border" v="0,170,0,100"/>
          <prop k="offset" v="0,0"/>
          <prop k="style" v="solid"/>
          <prop k="style_border" v="solid"/>
          <prop k="width_border" v="0.26"/>
        </layer>
        <layer pass="1" class="MarkerLine" locked="0">
          <prop k="interval" v="3"/>
          <prop k="offset" v="0"/>
          <prop k="placement" v="vertex"/>
          <prop k="rotate" v="1"/>
        </layer>
      </symbol>
      <symbol outputUnit="MM" alpha="0.4" type="fill" name="9">
        <layer pass="0" class="SimpleFill" locked="0">
          <prop k="color" v="170,85,255,102"/>
          <prop k="color_border" v="123,61,184,102"/>
          <prop k="offset" v="0,0"/>
          <prop k="style" v="solid"/>
          <prop k="style_border" v="solid"/>
          <prop k="width_border" v="0.26"/>
        </layer>
        <layer pass="0" class="MarkerLine" locked="0">
          <prop k="interval" v="3"/>
          <prop k="offset" v="0"/>
          <prop k="placement" v="vertex"/>
          <prop k="rotate" v="1"/>
        </layer>
      </symbol>
      <symbol outputUnit="MM" alpha="1" type="fill" name="default">
        <layer pass="0" class="SimpleFill" locked="0">
          <prop k="color" v="59,69,212,255"/>
          <prop k="color_border" v="0,0,0,255"/>
          <prop k="offset" v="0,0"/>
          <prop k="style" v="solid"/>
          <prop k="style_border" v="solid"/>
          <prop k="width_border" v="0.26"/>
        </layer>
      </symbol>
      <symbol outputUnit="MM" alpha="1" type="marker" name="@0@0">
        <layer pass="0" class="SimpleMarker" locked="0">
          <prop k="angle" v="0"/>
          <prop k="color" v="170,85,127,255"/>
          <prop k="color_border" v="170,85,127,255"/>
          <prop k="name" v="circle"/>
          <prop k="offset" v="0,0"/>
          <prop k="size" v="2"/>
        </layer>
      </symbol>
      <symbol outputUnit="MM" alpha="0.4" type="marker" name="@10@1">
        <layer pass="0" class="SimpleMarker" locked="0">
          <prop k="angle" v="0"/>
          <prop k="color" v="134,0,0,255"/>
          <prop k="color_border" v="134,0,0,255"/>
          <prop k="name" v="circle"/>
          <prop k="offset" v="0,0"/>
          <prop k="size" v="2"/>
        </layer>
      </symbol>
      <symbol outputUnit="MM" alpha="0.4980392156862745" type="marker" name="@11@1">
        <layer pass="0" class="SimpleMarker" locked="0">
          <prop k="angle" v="0"/>
          <prop k="color" v="0,170,0,255"/>
          <prop k="color_border" v="0,170,0,255"/>
          <prop k="name" v="circle"/>
          <prop k="offset" v="0,0"/>
          <prop k="size" v="2"/>
        </layer>
      </symbol>
      <symbol outputUnit="MM" alpha="0.4980392156862745" type="marker" name="@12@1">
        <layer pass="0" class="SimpleMarker" locked="0">
          <prop k="angle" v="0"/>
          <prop k="color" v="123,61,184,255"/>
          <prop k="color_border" v="123,61,184,255"/>
          <prop k="name" v="circle"/>
          <prop k="offset" v="0,0"/>
          <prop k="size" v="2"/>
        </layer>
      </symbol>
      <symbol outputUnit="MM" alpha="0.4980392156862745" type="marker" name="@13@1">
        <layer pass="0" class="SimpleMarker" locked="0">
          <prop k="angle" v="0"/>
          <prop k="color" v="134,0,0,255"/>
          <prop k="color_border" v="134,0,0,255"/>
          <prop k="name" v="circle"/>
          <prop k="offset" v="0,0"/>
          <prop k="size" v="2"/>
        </layer>
      </symbol>
      <symbol outputUnit="MM" alpha="1" type="marker" name="@1@0">
        <layer pass="0" class="SimpleMarker" locked="0">
          <prop k="angle" v="0"/>
          <prop k="color" v="255,162,2,255"/>
          <prop k="color_border" v="255,85,0,255"/>
          <prop k="name" v="circle"/>
          <prop k="offset" v="0,0"/>
          <prop k="size" v="2"/>
        </layer>
      </symbol>
      <symbol outputUnit="MM" alpha="0.3921568627450981" type="marker" name="@8@1">
        <layer pass="0" class="SimpleMarker" locked="0">
          <prop k="angle" v="0"/>
          <prop k="color" v="0,170,0,255"/>
          <prop k="color_border" v="0,170,0,255"/>
          <prop k="name" v="circle"/>
          <prop k="offset" v="0,0"/>
          <prop k="size" v="2"/>
        </layer>
      </symbol>
      <symbol outputUnit="MM" alpha="0.4" type="marker" name="@9@1">
        <layer pass="0" class="SimpleMarker" locked="0">
          <prop k="angle" v="0"/>
          <prop k="color" v="123,61,184,255"/>
          <prop k="color_border" v="123,61,184,255"/>
          <prop k="name" v="circle"/>
          <prop k="offset" v="0,0"/>
          <prop k="size" v="2"/>
        </layer>
      </symbol>
    </symbols>
  </renderer-v2>
  <customproperties>
    <property key="loadedByOmeroRTPlugin" value="VLID_GEOM_MODIF"/>
  </customproperties>
  <displayfield>ID_UV_NEW</displayfield>
  <label>0</label>
  <labelattributes>
    <label fieldname="" text="Etichetta"/>
    <family fieldname="" name="MS Shell Dlg 2"/>
    <size fieldname="" units="pt" value="12"/>
    <bold fieldname="" on="0"/>
    <italic fieldname="" on="0"/>
    <underline fieldname="" on="0"/>
    <strikeout fieldname="" on="0"/>
    <color fieldname="" red="0" blue="0" green="0"/>
    <x fieldname=""/>
    <y fieldname=""/>
    <offset x="0" y="0" units="pt" yfieldname="" xfieldname=""/>
    <angle fieldname="" value="0" auto="0"/>
    <alignment fieldname="" value="center"/>
    <buffercolor fieldname="" red="255" blue="255" green="255"/>
    <buffersize fieldname="" units="pt" value="1"/>
    <bufferenabled fieldname="" on=""/>
    <multilineenabled fieldname="" on=""/>
    <selectedonly on=""/>
  </labelattributes>
  <edittypes>
    <edittype type="0" name="ABBINATO_A_SCHEDA"/>
    <edittype type="0" name="GEOMETRIE_UNITA_VOLUMETRICHE_ORIGINALI_DI_PARTENZACODICE"/>
    <edittype type="0" name="ID_UV_NEW"/>
    <edittype type="0" name="NOTA"/>
    <edittype type="0" name="ZZ_STATO_GEOMETRIAID"/>
  </edittypes>
  <editform></editform>
  <editforminit></editforminit>
  <annotationform></annotationform>
  <attributeactions/>
</qgis>
