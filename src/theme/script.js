function getURLParams() {
  const queryParams = new URLSearchParams(window.location.search);
  const params = {};
  for (const [key, value] of queryParams.entries()) {
    params[key] = value;
  }
  return params;
}
$(document).ready(function () {
  const params = getURLParams();
  const search = params.search?.toLowerCase();
  $("#search").val(search);
  fetch("./redirects.json")
    .then((response) => {
      if (!response.ok) {
        throw new Error("HTTP error " + response.status);
      }
      return response.json();
    })
    .then((redirects) => {
      const results =
        search === undefined
          ? redirects
          : redirects.filter((x) => {
              return (
                x.name.includes(search) ||
                x.target.replace("-", " ").includes(search)
              );
            });
      if (results.length == 0) {
        $("#results").hide();
        $("#noresults").show();
        return;
      }
      for (let link of results) {
        $("#results").append(
          `<tr><td class="url"><input type="text" size="30" value="https://${
            window.location.host + "/" + link.name
          }" readonly></td><td class="target"><a href="${
            link.target
          }" target="_blank" title="Go to ${link.target}">Target</a></td></tr>`
        );
      }
    })
    .catch(console.error);
});
