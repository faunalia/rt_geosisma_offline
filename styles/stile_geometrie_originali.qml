<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis version="1.7.0-Wroclaw" minimumScale="0" maximumScale="1e+08" hasScaleBasedVisibilityFlag="0">
  <transparencyLevelInt>255</transparencyLevelInt>
  <renderer-v2 type="RuleRenderer">
    <rules>
      <rule scalemaxdenom="10000000" description="" filter="CODICE LIKE 'RT020101%'" symbol="0" scalemindenom="25000" label="Un.Vol : 1:25k - oltre"/>
      <rule scalemaxdenom="25000" description="" filter="CODICE LIKE 'RT020101%'" symbol="1" scalemindenom="2000" label="Un.Vol : 1:2k - 1:25k"/>
      <rule scalemaxdenom="2000" description="" filter="CODICE LIKE 'RT020101%'" symbol="2" scalemindenom="1" label="Un.Vol : 1:1 - 1:2k"/>
      <rule scalemaxdenom="10000000" description="" filter="CODICE LIKE 'RT020202%'" symbol="3" scalemindenom="25000" label="Manuf.Civile Monumentale Arredo : 1:25k - oltre"/>
      <rule scalemaxdenom="25000" description="" filter="CODICE LIKE 'RT020202%'" symbol="4" scalemindenom="2000" label="Manuf.Civile Monumentale Arredo : 1:2k - 1:25k"/>
      <rule scalemaxdenom="2000" description="" filter="CODICE LIKE 'RT020202%'" symbol="5" scalemindenom="1" label="Manuf.Civile Monumentale Arredo : 1:1 - 1:2k"/>
      <rule scalemaxdenom="10000000" description="" filter="CODICE LIKE 'RT020107%'" symbol="6" scalemindenom="25000" label="Aggetto : 1:25k - oltre"/>
      <rule scalemaxdenom="25000" description="" filter="CODICE LIKE 'RT020107%'" symbol="7" scalemindenom="2000" label="Aggetto : 1:2k - 1:25k"/>
      <rule scalemaxdenom="2000" description="" filter="CODICE LIKE 'RT020107%'" symbol="8" scalemindenom="1" label="Aggetto : 1:1 - 1:2k"/>
    </rules>
    <symbols>
      <symbol outputUnit="MM" alpha="1" type="fill" name="0">
        <layer pass="0" class="CentroidFill" locked="0"/>
      </symbol>
      <symbol outputUnit="MM" alpha="0.6" type="fill" name="1">
        <layer pass="0" class="SimpleFill" locked="0">
          <prop k="color" v="250,155,200,153"/>
          <prop k="color_border" v="255,135,200,153"/>
          <prop k="offset" v="0,0"/>
          <prop k="style" v="solid"/>
          <prop k="style_border" v="solid"/>
          <prop k="width_border" v="0.26"/>
        </layer>
      </symbol>
      <symbol outputUnit="MM" alpha="0.4" type="fill" name="2">
        <layer pass="0" class="SimpleFill" locked="0">
          <prop k="color" v="250,155,200,102"/>
          <prop k="color_border" v="240,110,200,102"/>
          <prop k="offset" v="0,0"/>
          <prop k="style" v="solid"/>
          <prop k="style_border" v="solid"/>
          <prop k="width_border" v="0.36"/>
        </layer>
        <layer pass="0" class="MarkerLine" locked="0">
          <prop k="interval" v="3"/>
          <prop k="offset" v="0"/>
          <prop k="placement" v="vertex"/>
          <prop k="rotate" v="1"/>
        </layer>
      </symbol>
      <symbol outputUnit="MM" alpha="1" type="fill" name="3">
        <layer pass="0" class="CentroidFill" locked="0"/>
      </symbol>
      <symbol outputUnit="MM" alpha="0.6" type="fill" name="4">
        <layer pass="0" class="SimpleFill" locked="0">
          <prop k="color" v="170,255,127,153"/>
          <prop k="color_border" v="132,196,97,153"/>
          <prop k="offset" v="0,0"/>
          <prop k="style" v="solid"/>
          <prop k="style_border" v="solid"/>
          <prop k="width_border" v="0.26"/>
        </layer>
      </symbol>
      <symbol outputUnit="MM" alpha="0.4" type="fill" name="5">
        <layer pass="0" class="SimpleFill" locked="0">
          <prop k="color" v="170,255,127,102"/>
          <prop k="color_border" v="170,255,127,102"/>
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
      <symbol outputUnit="MM" alpha="1" type="fill" name="6">
        <layer pass="0" class="CentroidFill" locked="0"/>
      </symbol>
      <symbol outputUnit="MM" alpha="0.6" type="fill" name="7">
        <layer pass="0" class="SimpleFill" locked="0">
          <prop k="color" v="170,255,255,153"/>
          <prop k="color_border" v="137,205,205,153"/>
          <prop k="offset" v="0,0"/>
          <prop k="style" v="solid"/>
          <prop k="style_border" v="solid"/>
          <prop k="width_border" v="0.26"/>
        </layer>
      </symbol>
      <symbol outputUnit="MM" alpha="0.4" type="fill" name="8">
        <layer pass="0" class="SimpleFill" locked="0">
          <prop k="color" v="170,255,255,102"/>
          <prop k="color_border" v="128,192,192,102"/>
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
          <prop k="color" v="30,236,236,255"/>
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
          <prop k="color" v="250,155,200,255"/>
          <prop k="color_border" v="250,155,200,255"/>
          <prop k="name" v="circle"/>
          <prop k="offset" v="0,0"/>
          <prop k="size" v="0.5"/>
        </layer>
      </symbol>
      <symbol outputUnit="MM" alpha="0.4" type="marker" name="@2@1">
        <layer pass="0" class="SimpleMarker" locked="0">
          <prop k="angle" v="0"/>
          <prop k="color" v="255,76,184,255"/>
          <prop k="color_border" v="0,0,0,255"/>
          <prop k="name" v="circle"/>
          <prop k="offset" v="0,0"/>
          <prop k="size" v="1"/>
        </layer>
      </symbol>
      <symbol outputUnit="MM" alpha="1" type="marker" name="@3@0">
        <layer pass="0" class="SimpleMarker" locked="0">
          <prop k="angle" v="0"/>
          <prop k="color" v="170,255,127,255"/>
          <prop k="color_border" v="170,255,127,255"/>
          <prop k="name" v="circle"/>
          <prop k="offset" v="0,0"/>
          <prop k="size" v="0.5"/>
        </layer>
      </symbol>
      <symbol outputUnit="MM" alpha="0.4" type="marker" name="@5@1">
        <layer pass="0" class="SimpleMarker" locked="0">
          <prop k="angle" v="0"/>
          <prop k="color" v="170,255,127,255"/>
          <prop k="color_border" v="0,0,0,255"/>
          <prop k="name" v="circle"/>
          <prop k="offset" v="0,0"/>
          <prop k="size" v="1"/>
        </layer>
      </symbol>
      <symbol outputUnit="MM" alpha="1" type="marker" name="@6@0">
        <layer pass="0" class="SimpleMarker" locked="0">
          <prop k="angle" v="0"/>
          <prop k="color" v="170,255,255,255"/>
          <prop k="color_border" v="170,255,255,255"/>
          <prop k="name" v="circle"/>
          <prop k="offset" v="0,0"/>
          <prop k="size" v="0.5"/>
        </layer>
      </symbol>
      <symbol outputUnit="MM" alpha="0.4" type="marker" name="@8@1">
        <layer pass="0" class="SimpleMarker" locked="0">
          <prop k="angle" v="0"/>
          <prop k="color" v="170,255,255,255"/>
          <prop k="color_border" v="0,0,0,255"/>
          <prop k="name" v="circle"/>
          <prop k="offset" v="0,0"/>
          <prop k="size" v="1"/>
        </layer>
      </symbol>
    </symbols>
  </renderer-v2>
  <customproperties>
    <property key="loadedByOmeroRTPlugin" value="VLID_GEOM_ORIG"/>
  </customproperties>
  <displayfield>CODICE</displayfield>
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
    <edittype type="0" name="CODICE"/>
  </edittypes>
  <editform></editform>
  <editforminit></editforminit>
  <annotationform></annotationform>
  <attributeactions/>
</qgis>
