let products = JSON.parse(document.getElementById("productsData")?.textContent || "[]");

function addRow(product=null){
let tr=document.createElement("tr");

tr.innerHTML=`
<td>
<select class="product">
<option value="">Select</option>
${products.map(p=>`
<option value="${p.id}" data-price="${p.price}" data-barcode="${p.barcode}">
${p.name}
</option>`).join("")}
</select>
</td>
<td><input type="number" class="qty" value="1"></td>
<td><input type="number" class="price"></td>
<td class="total">0</td>
<td><button onclick="this.closest('tr').remove()">✕</button></td>
`;

document.getElementById("orderBody").appendChild(tr);
}

document.getElementById("addRow").onclick=()=>addRow();

function recalc(){
let sub=0;
document.querySelectorAll("#orderBody tr").forEach(tr=>{
let q=+tr.querySelector(".qty").value||0;
let p=+tr.querySelector(".price").value||0;
let t=q*p;
tr.querySelector(".total").innerText=t.toFixed(2);
sub+=t;
});
document.getElementById("subTotal").innerText=sub.toFixed(2);
document.getElementById("tax").innerText=(sub*0.18).toFixed(2);
document.getElementById("grandTotal").innerText=(sub*1.18).toFixed(2);
}
document.addEventListener("input",recalc);

// QR / BARCODE
document.getElementById("startScan").onclick=()=>{
new Html5Qrcode("scanner").start(
{facingMode:"environment"},
{fps:10,qrbox:250},
(code)=>{
let row=[...document.querySelectorAll(".product option")]
.find(o=>o.dataset.barcode===code);
if(row){
addRow();
let last=document.querySelector("#orderBody tr:last-child select");
last.value=row.value;
last.dispatchEvent(new Event("change"));
}
}
);
};
